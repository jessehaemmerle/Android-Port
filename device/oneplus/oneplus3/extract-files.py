#!/usr/bin/env -S PYTHONPATH=../../../tools/extract-utils python3
#
# SPDX-FileCopyrightText: 2016 The CyanogenMod Project
# SPDX-FileCopyrightText: 2017-2024 The LineageOS Project
# SPDX-License-Identifier: Apache-2.0
#
# lineage-23.0 liefert tools/extract-utils nur noch in Python (geprueft: Zweig
# lineage-23.0 enthaelt kein extract_utils.sh mehr). Dieses Skript ersetzt
# extract-files.sh und setup-makefiles.sh. Aufruf: ./extract-files.py [-n] [-k] [Quelle]

from extract_utils.fixups_blob import (
    blob_fixup,
    blob_fixups_user_type,
)
from extract_utils.main import (
    ExtractUtils,
    ExtractUtilsModule,
)

namespace_imports = [
    'device/oneplus/oneplus3',
    'hardware/qcom-caf/msm8996/audio',
    'hardware/qcom-caf/msm8996/display',
    'hardware/qcom-caf/msm8996/media',
]

blob_fixups: blob_fixups_user_type = {
    # Alte Protobuf-Namen: hardware/lineage/compat liefert libprotobuf-cpp-*-vendorcompat
    # unter dem Originalnamen, ein replace_needed ist nicht mehr noetig.
    ('vendor/lib/hw/vulkan.msm8996.so', 'vendor/lib64/hw/vulkan.msm8996.so'): blob_fixup()
        .fix_soname(),
    'etc/permissions/qti_libpermissions.xml': blob_fixup()
        .regex_replace('name="android.hidl.manager-V1.0-java', 'name="android.hidl.manager@1.0-java'),
}  # fmt: skip

module = ExtractUtilsModule(
    'oneplus3',
    'oneplus',
    blob_fixups=blob_fixups,
    namespace_imports=namespace_imports,
)

if __name__ == '__main__':
    utils = ExtractUtils.device(module)
    utils.run()
