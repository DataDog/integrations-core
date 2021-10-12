#  (C) Datadog, Inc. 2020-present
#  All rights reserved
#  Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os

import jsonschema
import requests

import datadog_checks.dev.tooling.manifest_validator.common.validator as common
from datadog_checks.dev.tooling.manifest_validator.common.validator import BaseManifestValidator

from ...constants import get_root
from ..constants import V2

METRIC_TO_CHECK_EXCLUDE_LIST = {
    'openstack.controller',  # "Artificial" metric, shouldn't be listed in metadata file.
    'riakcs.bucket_list_pool.workers',  # RiakCS 2.1 metric, but metadata.csv lists RiakCS 2.0 metrics only.
}


class DisplayOnPublicValidator(BaseManifestValidator):
    def validate(self, check_name, decoded, fix):
        correct_is_public = True
        path = '/display_on_public_website'
        is_public = decoded.get_path(path)
        if not isinstance(is_public, bool):
            output = '  required boolean: display_on_public_website'

            if fix:
                decoded.set_path(path, correct_is_public)
                self.fix(output, f'  new `display_on_public_website`: {correct_is_public}')
            else:
                self.fail(output)


class SchemaValidator(BaseManifestValidator):
    def validate(self, check_name, decoded, fix):
        if not self.should_validate():
            return

        # Get API and APP keys which are needed to call Datadog API
        org_name = self.ctx.obj.get('org')
        if not org_name:
            self.fail('No `org` has been set')
            return

        if org_name not in self.ctx.obj.get('orgs'):
            self.fail(f'Selected org {org_name} is not in `orgs`')
            return

        org = self.ctx.obj['orgs'][org_name]

        dd_url = org.get('dd_url')
        if not dd_url:
            self.fail(f'No `dd_url` has been set for org `{org_name}`')
            return

        url = f"{dd_url}/api/beta/apps/manifest/validate"

        # prep for upload
        payload = {"data": {"type": "app_manifest", "attributes": decoded}}

        try:
            payload_json = json.dumps(payload)
            r = requests.post(url, data=payload_json)

            if r.status_code == 400:
                # parse the errors
                errors = "\n".join(r.json()["errors"])
                message = f"Error validating manifest schema:\n{errors}"
                self.fail(message)
            else:
                r.raise_for_status()
        except Exception as e:
            self.fail(str(e))


class MediaGalleryValidator(BaseManifestValidator):
    VIDEO_MEDIA_ATTRIBUTES = ('media_type', 'caption', 'image_url', 'vimeo_id')
    IMAGE_MEDIA_ATTRIBUTES = ('media_type', 'caption', 'image_url')
    MEDIA_PATH = '/tile/media'
    MAX_MEDIA_ELEMENTS = 8

    IMAGE_SCHEMA = jsonschema.Draft7Validator(
        {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "V2 Manifest Image Media Element Validator",
            "description": "Defines the various components of an image media element",
            "type": "object",
            "properties": {
                "media_type": {
                    "description": "The type of media (image or video)",
                    "type": "string",
                    "enum": ["image"],
                },
                "caption": {
                    "description": "The caption for this image media",
                    "type": "string",
                },
                "image_url": {
                    "description": "The relative path to the image from integration root",
                    "type": "string",
                },
            },
            "required": ["media_type", "caption", "image_url"],
        }
    )
    VIDEO_SCHEMA = jsonschema.Draft7Validator(
        {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "V2 Manifest Video Media Element Validator",
            "description": "Defines the various components of a video media element",
            "type": "object",
            "properties": {
                "media_type": {
                    "description": "The type of media (image or video)",
                    "type": "string",
                    "enum": ["video"],
                },
                "caption": {
                    "description": "The caption for this video media",
                    "type": "string",
                },
                "image_url": {
                    "description": "The relative path to the image from integration root",
                    "type": "string",
                },
                "vimeo_id": {
                    "description": "The vimeo id (9 digits) corresponding to this video",
                    "type": "integer",
                },
            },
            "required": ["media_type", "caption", "image_url", "vimeo_id"],
        }
    )

    def validate(self, check_name, decoded, fix):
        if not self.should_validate():
            return

        media_array = decoded.get_path(self.MEDIA_PATH)
        # Skip validations if no media is included in the manifest
        if not media_array:
            return

        # Length must be between 1-8
        num_media_elements = len(media_array)
        if num_media_elements > self.MAX_MEDIA_ELEMENTS:
            output = f'  The maximum number of media elements is 8, there are currently {num_media_elements}.'
            self.fail(output)

        # Validate each media object
        video_count = 0
        for i, media in enumerate(media_array, 1):
            # Ensure each media contains valid keys
            try:
                media_type = media['media_type']
                if media_type == 'image':
                    attribute_schema = self.IMAGE_SCHEMA
                elif media_type == 'video':
                    attribute_schema = self.VIDEO_SCHEMA
                else:
                    output = f'  Media #{i} `media_type` attribute must be "video" or "image"'
                    self.fail(output)
                    continue

                # Validate with the correct schema
                errors = sorted(attribute_schema.iter_errors(media), key=lambda e: e.path)
                if errors:
                    for error in errors:
                        self.fail(f'  Media #{i}: {error.message}')
                    continue
            except KeyError:
                output = f'  Media #{i}: \'media_type\' is a required property'
                self.fail(output)
                continue

            caption = media['caption']
            image_url = media['image_url']

            # Image_url must lead to png or jpg
            if '.png' not in image_url.lower() and '.jpg' not in image_url.lower():
                output = f'  The filetype for media #{i} must be either `.jpg` or `.png`.'
                self.fail(output)

            # Caption must be smaller than 300 chars
            if len(caption) > 300:
                output = f'  The `caption` for media #{i} cannot contain more than 300 characters.'
                self.fail(output)

            # Keep track of video count (only 1 is allowed)
            if media_type == 'video':
                video_count += 1

            try:
                # Check if file is found in directory
                cur_path = os.path.join(get_root(), check_name)
                file_size = os.path.getsize(f'{cur_path}/{image_url}')
                if file_size > 1000000:  # If file size greater than 1 megabyte, fail
                    output = f'  File size for media #{i} must be smaller than 1 mb, currently {file_size} bytes.'
                    self.fail(output)
            except OSError:
                output = f'  File not found for media #{i} at `{image_url}`, please fix the path.'
                self.fail(output)

        if video_count > 1:
            output = f'  There cannot be more than 1 video in the list of media, currently there are {video_count}'
            self.fail(output)


def get_v2_validators(ctx, is_extras, is_marketplace):
    return [
        common.MaintainerValidator(
            is_extras, is_marketplace, check_in_extras=False, check_in_marketplace=False, version=V2
        ),
        common.MetricsMetadataValidator(version=V2),
        common.MetricToCheckValidator(version=V2),
        common.ImmutableAttributesValidator(version=V2),
        common.LogsCategoryValidator(version=V2),
        DisplayOnPublicValidator(version=V2),
        MediaGalleryValidator(is_marketplace, is_extras, version=V2),
        # keep SchemaValidator last, and avoid running this validation if errors already found
        SchemaValidator(ctx=ctx, version=V2, skip_if_errors=True),
    ]
