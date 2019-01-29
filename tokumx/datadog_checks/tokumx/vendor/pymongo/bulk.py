# Copyright 2014-2015 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""The bulk write operations interface.

.. versionadded:: 2.7
"""

from bson.objectid import ObjectId
from bson.raw_bson import RawBSONDocument
from bson.son import SON
from pymongo.common import (validate_is_mapping,
                            validate_is_document_type,
                            validate_ok_for_replace,
                            validate_ok_for_update)
from pymongo.collation import validate_collation_or_none
from pymongo.errors import (BulkWriteError,
                            ConfigurationError,
                            DocumentTooLarge,
                            InvalidOperation,
                            OperationFailure)
from pymongo.message import (_INSERT, _UPDATE, _DELETE,
                             _do_batched_write_command,
                             _randint,
                             _BulkWriteContext)
from pymongo.write_concern import WriteConcern


_DELETE_ALL = 0
_DELETE_ONE = 1

# For backwards compatibility. See MongoDB src/mongo/base/error_codes.err
_BAD_VALUE = 2
_UNKNOWN_ERROR = 8
_WRITE_CONCERN_ERROR = 64

_COMMANDS = ('insert', 'update', 'delete')


# These string literals are used when we create fake server return
# documents client side. We use unicode literals in python 2.x to
# match the actual return values from the server.
_UID = u"_id"
_UCODE = u"code"
_UERRMSG = u"errmsg"
_UINDEX = u"index"
_UOP = u"op"


class _Run(object):
    """Represents a batch of write operations.
    """
    def __init__(self, op_type):
        """Initialize a new Run object.
        """
        self.op_type = op_type
        self.index_map = []
        self.ops = []

    def index(self, idx):
        """Get the original index of an operation in this run.

        :Parameters:
          - `idx`: The Run index that maps to the original index.
        """
        return self.index_map[idx]

    def add(self, original_index, operation):
        """Add an operation to this Run instance.

        :Parameters:
          - `original_index`: The original index of this operation
            within a larger bulk operation.
          - `operation`: The operation document.
        """
        self.index_map.append(original_index)
        self.ops.append(operation)


def _make_error(index, code, errmsg, operation):
    """Create and return an error document.
    """
    return {
        _UINDEX: index,
        _UCODE: code,
        _UERRMSG: errmsg,
        _UOP: operation
    }


def _merge_legacy(run, full_result, result, index):
    """Merge a result from a legacy opcode into the full results.
    """
    affected = result.get('n', 0)

    errmsg = result.get("errmsg", result.get("err", ""))
    if errmsg:
        # wtimeout is not considered a hard failure in
        # MongoDB 2.6 so don't treat it like one here.
        if result.get("wtimeout"):
            error_doc = {'errmsg': errmsg, 'code': _WRITE_CONCERN_ERROR}
            full_result['writeConcernErrors'].append(error_doc)
        else:
            code = result.get("code", _UNKNOWN_ERROR)
            error = _make_error(run.index(index), code, errmsg, run.ops[index])
            if "errInfo" in result:
                error["errInfo"] = result["errInfo"]
            full_result["writeErrors"].append(error)
            return
    if run.op_type == _INSERT:
        full_result['nInserted'] += 1
    elif run.op_type == _UPDATE:
        if "upserted" in result:
            doc = {_UINDEX: run.index(index), _UID: result["upserted"]}
            full_result["upserted"].append(doc)
            full_result['nUpserted'] += affected
        # Versions of MongoDB before 2.6 don't return the _id for an
        # upsert if _id is not an ObjectId.
        elif result.get("updatedExisting") is False and affected == 1:
            op = run.ops[index]
            # If _id is in both the update document *and* the query spec
            # the update document _id takes precedence.
            _id = op['u'].get('_id', op['q'].get('_id'))
            doc = {_UINDEX: run.index(index), _UID: _id}
            full_result["upserted"].append(doc)
            full_result['nUpserted'] += affected
        else:
            full_result['nMatched'] += affected

    elif run.op_type == _DELETE:
        full_result['nRemoved'] += affected


def _merge_command(run, full_result, results):
    """Merge a group of results from write commands into the full result.
    """
    for offset, result in results:

        affected = result.get("n", 0)

        if run.op_type == _INSERT:
            full_result["nInserted"] += affected

        elif run.op_type == _DELETE:
            full_result["nRemoved"] += affected

        elif run.op_type == _UPDATE:
            upserted = result.get("upserted")
            if upserted:
                if isinstance(upserted, list):
                    n_upserted = len(upserted)
                    for doc in upserted:
                        doc["index"] = run.index(doc["index"] + offset)
                    full_result["upserted"].extend(upserted)
                else:
                    n_upserted = 1
                    index = run.index(offset)
                    doc = {_UINDEX: index, _UID: upserted}
                    full_result["upserted"].append(doc)
                full_result["nUpserted"] += n_upserted
                full_result["nMatched"] += (affected - n_upserted)
            else:
                full_result["nMatched"] += affected
            n_modified = result.get("nModified")
            # SERVER-13001 - in a mixed sharded cluster a call to
            # update could return nModified (>= 2.6) or not (<= 2.4).
            # If any call does not return nModified we can't report
            # a valid final count so omit the field completely.
            if n_modified is not None and "nModified" in full_result:
                full_result["nModified"] += n_modified
            else:
                full_result.pop("nModified", None)

        write_errors = result.get("writeErrors")
        if write_errors:
            for doc in write_errors:
                # Leave the server response intact for APM.
                replacement = doc.copy()
                idx = doc["index"] + offset
                replacement["index"] = run.index(idx)
                # Add the failed operation to the error document.
                replacement[_UOP] = run.ops[idx]
                full_result["writeErrors"].append(replacement)

        wc_error = result.get("writeConcernError")
        if wc_error:
            full_result["writeConcernErrors"].append(wc_error)


class _Bulk(object):
    """The private guts of the bulk write API.
    """
    def __init__(self, collection, ordered, bypass_document_validation):
        """Initialize a _Bulk instance.
        """
        self.collection = collection.with_options(
            codec_options=collection.codec_options._replace(
                unicode_decode_error_handler='replace',
                document_class=dict))
        self.ordered = ordered
        self.ops = []
        self.name = "%s.%s" % (collection.database.name, collection.name)
        self.namespace = collection.database.name + '.$cmd'
        self.executed = False
        self.bypass_doc_val = bypass_document_validation
        self.uses_collation = False

    def add_insert(self, document):
        """Add an insert document to the list of ops.
        """
        validate_is_document_type("document", document)
        # Generate ObjectId client side.
        if not (isinstance(document, RawBSONDocument) or '_id' in document):
            document['_id'] = ObjectId()
        self.ops.append((_INSERT, document))

    def add_update(self, selector, update, multi=False, upsert=False,
                   collation=None):
        """Create an update document and add it to the list of ops.
        """
        validate_ok_for_update(update)
        cmd = SON([('q', selector), ('u', update),
                   ('multi', multi), ('upsert', upsert)])
        collation = validate_collation_or_none(collation)
        if collation is not None:
            self.uses_collation = True
            cmd['collation'] = collation
        self.ops.append((_UPDATE, cmd))

    def add_replace(self, selector, replacement, upsert=False,
                    collation=None):
        """Create a replace document and add it to the list of ops.
        """
        validate_ok_for_replace(replacement)
        cmd = SON([('q', selector), ('u', replacement),
                   ('multi', False), ('upsert', upsert)])
        collation = validate_collation_or_none(collation)
        if collation is not None:
            self.uses_collation = True
            cmd['collation'] = collation
        self.ops.append((_UPDATE, cmd))

    def add_delete(self, selector, limit, collation=None):
        """Create a delete document and add it to the list of ops.
        """
        cmd = SON([('q', selector), ('limit', limit)])
        collation = validate_collation_or_none(collation)
        if collation is not None:
            self.uses_collation = True
            cmd['collation'] = collation
        self.ops.append((_DELETE, cmd))

    def gen_ordered(self):
        """Generate batches of operations, batched by type of
        operation, in the order **provided**.
        """
        run = None
        for idx, (op_type, operation) in enumerate(self.ops):
            if run is None:
                run = _Run(op_type)
            elif run.op_type != op_type:
                yield run
                run = _Run(op_type)
            run.add(idx, operation)
        yield run

    def gen_unordered(self):
        """Generate batches of operations, batched by type of
        operation, in arbitrary order.
        """
        operations = [_Run(_INSERT), _Run(_UPDATE), _Run(_DELETE)]
        for idx, (op_type, operation) in enumerate(self.ops):
            operations[op_type].add(idx, operation)

        for run in operations:
            if run.ops:
                yield run

    def execute_command(self, sock_info, generator, write_concern):
        """Execute using write commands.
        """
        # nModified is only reported for write commands, not legacy ops.
        full_result = {
            "writeErrors": [],
            "writeConcernErrors": [],
            "nInserted": 0,
            "nUpserted": 0,
            "nMatched": 0,
            "nModified": 0,
            "nRemoved": 0,
            "upserted": [],
        }
        op_id = _randint()
        db_name = self.collection.database.name
        listeners = self.collection.database.client._event_listeners

        for run in generator:
            cmd = SON([(_COMMANDS[run.op_type], self.collection.name),
                       ('ordered', self.ordered)])
            if write_concern.document:
                cmd['writeConcern'] = write_concern.document
            if self.bypass_doc_val and sock_info.max_wire_version >= 4:
                cmd['bypassDocumentValidation'] = True

            bwc = _BulkWriteContext(db_name, cmd, sock_info, op_id, listeners)
            results = _do_batched_write_command(
                self.namespace, run.op_type, cmd,
                run.ops, True, self.collection.codec_options, bwc)

            _merge_command(run, full_result, results)
            # We're supposed to continue if errors are
            # at the write concern level (e.g. wtimeout)
            if self.ordered and full_result['writeErrors']:
                break

        if full_result["writeErrors"] or full_result["writeConcernErrors"]:
            if full_result['writeErrors']:
                full_result['writeErrors'].sort(
                    key=lambda error: error['index'])
            raise BulkWriteError(full_result)
        return full_result

    def execute_no_results(self, sock_info, generator):
        """Execute all operations, returning no results (w=0).
        """
        # Cannot have both unacknowledged write and bypass document validation.
        if self.bypass_doc_val and sock_info.max_wire_version >= 4:
            raise OperationFailure("Cannot set bypass_document_validation with"
                                   " unacknowledged write concern")
        coll = self.collection
        # If ordered is True we have to send GLE or use write
        # commands so we can abort on the first error.
        write_concern = WriteConcern(w=int(self.ordered))
        op_id = _randint()

        for run in generator:
            try:
                if run.op_type == _INSERT:
                    coll._insert(
                        sock_info,
                        run.ops,
                        self.ordered,
                        write_concern=write_concern,
                        op_id=op_id,
                        bypass_doc_val=self.bypass_doc_val)
                elif run.op_type == _UPDATE:
                    for operation in run.ops:
                        doc = operation['u']
                        check_keys = True
                        if doc and next(iter(doc)).startswith('$'):
                            check_keys = False
                        coll._update(
                            sock_info,
                            operation['q'],
                            doc,
                            operation['upsert'],
                            check_keys,
                            operation['multi'],
                            write_concern=write_concern,
                            op_id=op_id,
                            ordered=self.ordered,
                            bypass_doc_val=self.bypass_doc_val)
                else:
                    for operation in run.ops:
                        coll._delete(sock_info,
                                     operation['q'],
                                     not operation['limit'],
                                     write_concern,
                                     op_id,
                                     self.ordered)
            except OperationFailure:
                if self.ordered:
                    break

    def execute_legacy(self, sock_info, generator, write_concern):
        """Execute using legacy wire protocol ops.
        """
        coll = self.collection
        full_result = {
            "writeErrors": [],
            "writeConcernErrors": [],
            "nInserted": 0,
            "nUpserted": 0,
            "nMatched": 0,
            "nRemoved": 0,
            "upserted": [],
        }
        op_id = _randint()
        stop = False
        for run in generator:
            for idx, operation in enumerate(run.ops):
                try:
                    # To do per-operation reporting we have to do ops one
                    # at a time. That means the performance of bulk insert
                    # will be slower here than calling Collection.insert()
                    if run.op_type == _INSERT:
                        coll._insert(sock_info,
                                     operation,
                                     self.ordered,
                                     write_concern=write_concern,
                                     op_id=op_id)
                        result = {}
                    elif run.op_type == _UPDATE:
                        doc = operation['u']
                        check_keys = True
                        if doc and next(iter(doc)).startswith('$'):
                            check_keys = False
                        result = coll._update(sock_info,
                                              operation['q'],
                                              doc,
                                              operation['upsert'],
                                              check_keys,
                                              operation['multi'],
                                              write_concern=write_concern,
                                              op_id=op_id,
                                              ordered=self.ordered)
                    else:
                        result = coll._delete(sock_info,
                                              operation['q'],
                                              not operation['limit'],
                                              write_concern,
                                              op_id,
                                              self.ordered)
                    _merge_legacy(run, full_result, result, idx)
                except DocumentTooLarge as exc:
                    # MongoDB 2.6 uses error code 2 for "too large".
                    error = _make_error(
                        run.index(idx), _BAD_VALUE, str(exc), operation)
                    full_result['writeErrors'].append(error)
                    if self.ordered:
                        stop = True
                        break
                except OperationFailure as exc:
                    if not exc.details:
                        # Some error not related to the write operation
                        # (e.g. kerberos failure). Re-raise immediately.
                        raise
                    _merge_legacy(run, full_result, exc.details, idx)
                    # We're supposed to continue if errors are
                    # at the write concern level (e.g. wtimeout)
                    if self.ordered and full_result["writeErrors"]:
                        stop = True
                        break
            if stop:
                break

        if full_result["writeErrors"] or full_result['writeConcernErrors']:
            if full_result['writeErrors']:
                full_result['writeErrors'].sort(
                    key=lambda error: error['index'])
            raise BulkWriteError(full_result)
        return full_result

    def execute(self, write_concern):
        """Execute operations.
        """
        if not self.ops:
            raise InvalidOperation('No operations to execute')
        if self.executed:
            raise InvalidOperation('Bulk operations can '
                                   'only be executed once.')
        self.executed = True
        write_concern = (WriteConcern(**write_concern) if
                         write_concern else self.collection.write_concern)

        if self.ordered:
            generator = self.gen_ordered()
        else:
            generator = self.gen_unordered()

        client = self.collection.database.client
        with client._socket_for_writes() as sock_info:
            if sock_info.max_wire_version < 5 and self.uses_collation:
                raise ConfigurationError(
                    'Must be connected to MongoDB 3.4+ to use a collation.')
            if not write_concern.acknowledged:
                if self.uses_collation:
                    raise ConfigurationError(
                        'Collation is unsupported for unacknowledged writes.')
                self.execute_no_results(sock_info, generator)
            elif sock_info.max_wire_version > 1:
                return self.execute_command(sock_info, generator, write_concern)
            else:
                return self.execute_legacy(sock_info, generator, write_concern)


class BulkUpsertOperation(object):
    """An interface for adding upsert operations.
    """

    __slots__ = ('__selector', '__bulk', '__collation')

    def __init__(self, selector, bulk, collation):
        self.__selector = selector
        self.__bulk = bulk
        self.__collation = collation

    def update_one(self, update):
        """Update one document matching the selector.

        :Parameters:
          - `update` (dict): the update operations to apply
        """
        self.__bulk.add_update(self.__selector,
                               update, multi=False, upsert=True,
                               collation=self.__collation)

    def update(self, update):
        """Update all documents matching the selector.

        :Parameters:
          - `update` (dict): the update operations to apply
        """
        self.__bulk.add_update(self.__selector,
                               update, multi=True, upsert=True,
                               collation=self.__collation)

    def replace_one(self, replacement):
        """Replace one entire document matching the selector criteria.

        :Parameters:
          - `replacement` (dict): the replacement document
        """
        self.__bulk.add_replace(self.__selector, replacement, upsert=True,
                                collation=self.__collation)


class BulkWriteOperation(object):
    """An interface for adding update or remove operations.
    """

    __slots__ = ('__selector', '__bulk', '__collation')

    def __init__(self, selector, bulk, collation):
        self.__selector = selector
        self.__bulk = bulk
        self.__collation = collation

    def update_one(self, update):
        """Update one document matching the selector criteria.

        :Parameters:
          - `update` (dict): the update operations to apply
        """
        self.__bulk.add_update(self.__selector, update, multi=False,
                               collation=self.__collation)

    def update(self, update):
        """Update all documents matching the selector criteria.

        :Parameters:
          - `update` (dict): the update operations to apply
        """
        self.__bulk.add_update(self.__selector, update, multi=True,
                               collation=self.__collation)

    def replace_one(self, replacement):
        """Replace one entire document matching the selector criteria.

        :Parameters:
          - `replacement` (dict): the replacement document
        """
        self.__bulk.add_replace(self.__selector, replacement,
                                collation=self.__collation)

    def remove_one(self):
        """Remove a single document matching the selector criteria.
        """
        self.__bulk.add_delete(self.__selector, _DELETE_ONE,
                               collation=self.__collation)

    def remove(self):
        """Remove all documents matching the selector criteria.
        """
        self.__bulk.add_delete(self.__selector, _DELETE_ALL,
                               collation=self.__collation)

    def upsert(self):
        """Specify that all chained update operations should be
        upserts.

        :Returns:
          - A :class:`BulkUpsertOperation` instance, used to add
            update operations to this bulk operation.
        """
        return BulkUpsertOperation(self.__selector, self.__bulk,
                                   self.__collation)


class BulkOperationBuilder(object):
    """**DEPRECATED**: An interface for executing a batch of write operations.
    """

    __slots__ = '__bulk'

    def __init__(self, collection, ordered=True,
                 bypass_document_validation=False):
        """**DEPRECATED**: Initialize a new BulkOperationBuilder instance.

        :Parameters:
          - `collection`: A :class:`~pymongo.collection.Collection` instance.
          - `ordered` (optional): If ``True`` all operations will be executed
            serially, in the order provided, and the entire execution will
            abort on the first error. If ``False`` operations will be executed
            in arbitrary order (possibly in parallel on the server), reporting
            any errors that occurred after attempting all operations. Defaults
            to ``True``.
          - `bypass_document_validation`: (optional) If ``True``, allows the
            write to opt-out of document level validation. Default is
            ``False``.

        .. note:: `bypass_document_validation` requires server version
          **>= 3.2**

        .. versionchanged:: 3.5
           Deprecated. Use :meth:`~pymongo.collection.Collection.bulk_write`
           instead.

        .. versionchanged:: 3.2
          Added bypass_document_validation support
        """
        self.__bulk = _Bulk(collection, ordered, bypass_document_validation)

    def find(self, selector, collation=None):
        """Specify selection criteria for bulk operations.

        :Parameters:
          - `selector` (dict): the selection criteria for update
            and remove operations.
          - `collation` (optional): An instance of
            :class:`~pymongo.collation.Collation`. This option is only
            supported on MongoDB 3.4 and above.

        :Returns:
          - A :class:`BulkWriteOperation` instance, used to add
            update and remove operations to this bulk operation.

        .. versionchanged:: 3.4
           Added the `collation` option.

        """
        validate_is_mapping("selector", selector)
        return BulkWriteOperation(selector, self.__bulk, collation)

    def insert(self, document):
        """Insert a single document.

        :Parameters:
          - `document` (dict): the document to insert

        .. seealso:: :ref:`writes-and-ids`
        """
        self.__bulk.add_insert(document)

    def execute(self, write_concern=None):
        """Execute all provided operations.

        :Parameters:
          - write_concern (optional): the write concern for this bulk
            execution.
        """
        if write_concern is not None:
            validate_is_mapping("write_concern", write_concern)
        return self.__bulk.execute(write_concern)
