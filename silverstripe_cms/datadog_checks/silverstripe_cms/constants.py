# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from .dataclasses import TableConfig

# Field validation constants
REQUIRED_STRING_FIELDS = [
    "SILVERSTRIPE_DATABASE_TYPE",
    "SILVERSTRIPE_DATABASE_NAME",
    "SILVERSTRIPE_DATABASE_SERVER_IP",
    "SILVERSTRIPE_DATABASE_USERNAME",
    "SILVERSTRIPE_DATABASE_PASSWORD",
]
REQUIRED_INTEGER_FIELDS = ["SILVERSTRIPE_DATABASE_PORT", "min_collection_interval"]
SUPPORTED_DATABASE_TYPES = ["PostgreSQL", "MySQL"]
IPV4_PATTERN = r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
MIN_PORT = 0
MAX_PORT = 65535
MIN_COLLECTION_INTERVAL = 1
MAX_COLLECTION_INTERVAL = 64800

# ServiceCheck and Events constants
INTEGRATION_PREFIX = "Silverstripe.CMS"
SILVERSTRIPE_CMS_CHECK_NAME = "status"
CONF_VAL_TAG = ["tag:silverstripe_cms_conf_validation"]
CONF_VAL_TITLE = "Silverstripe CMS conf.yaml validations"
CONF_VAL_SOURCE_TYPE = INTEGRATION_PREFIX + ".silverstripe_cms_conf_validation"
STATUS_NUMBER_TO_VALUE = {0: "SUCCESS", 1: "WARNING", 2: "ERROR"}
AUTH_TAG = ["tag:silverstripe_cms_authentication"]
AUTH_TITLE = "Silverstripe CMS Authentication"
AUTH_SOURCE_TYPE = INTEGRATION_PREFIX + ".silverstipe_cms_authentication"

# Silverstripe CMS Database Constants
MYSQL = "MySQL"
DB_CONNECTION_TIMEOUT_IN_SECONDS = 10

# Tables
FILE = "File"
FILE_LIVE = "File_Live"
SITE_TREE = "SiteTree"
SITE_TREE_LIVE = "SiteTree_Live"
SITE_TREE_VERSIONS = "SiteTree_Versions"

# Conditions
ANYONE_CAN_VIEW = ("CanViewType", "=", "Anyone")
HAS_BROKEN_LINK = ("HasBrokenLink", "=", 1)
HAS_BROKEN_FILE = ("HasBrokenFile", "=", 1)
WAS_DELETED = ("WasDeleted", "=", 1)
WAS_PUBLISHED = ("WasPublished", "=", 1)

# Operators
OR = "OR"

# Mappings
METRIC_TO_TABLE_CONFIG_MAPPING = {
    "files.count": TableConfig(name=FILE),
    "files.public_count": TableConfig(name=FILE, conditions=[ANYONE_CAN_VIEW]),
    "files_live.count": TableConfig(name=FILE_LIVE),
    "files_live.public_count": TableConfig(name=FILE_LIVE, conditions=[ANYONE_CAN_VIEW]),
    "pages.count": TableConfig(name=SITE_TREE),
    "pages.broken_link_count": TableConfig(name=SITE_TREE, conditions=[HAS_BROKEN_LINK]),
    "pages.broken_file_count": TableConfig(name=SITE_TREE, conditions=[HAS_BROKEN_FILE]),
    "pages.broken_content": TableConfig(
        name=SITE_TREE, conditions=[HAS_BROKEN_LINK, HAS_BROKEN_FILE], conditional_operator=OR
    ),
    "pages_live.count": TableConfig(name=SITE_TREE_LIVE),
    "pages_live.broken_link_count": TableConfig(name=SITE_TREE_LIVE, conditions=[HAS_BROKEN_LINK]),
    "pages_live.broken_file_count": TableConfig(name=SITE_TREE_LIVE, conditions=[HAS_BROKEN_FILE]),
    "pages_live.broken_content": TableConfig(
        name=SITE_TREE_LIVE, conditions=[HAS_BROKEN_LINK, HAS_BROKEN_FILE], conditional_operator=OR
    ),
    "pages_live.deleted_count": TableConfig(name=SITE_TREE_VERSIONS, conditions=[WAS_DELETED, WAS_PUBLISHED]),
}

METRIC_TO_QUERY_MAPPING = {
    "failed_login_count": """SELECT `MemberID` as member_id, COUNT(*) AS `RowCount`, `IP`, `FirstName`, `Surname`
        FROM `LoginAttempt` JOIN `Member` `m` ON `MemberID` = `m`.`ID` WHERE `Status` = 'Failure'
        GROUP BY `MemberID`, `IP`, `FirstName`, `Surname`""",
}

# tags configuration
CLASSNAME_TO_TAG_MAPPING = {
    "Page": "page_type:page",
    "ErrorPage": "page_type:error_page",
    "RedirectorPage": "page_type:redirector_page",
    "VirtualPage": "page_type:virtual_page",
    "File": "file_type:file",
    "Image": "file_type:image",
}

LOG_TEMPLATE = "Silverstripe CMS | HOST={host} | MESSAGE={message}"
