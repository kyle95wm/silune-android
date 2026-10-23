#!/usr/bin/env python3
"""Fail a daily merge if it changes the fork's HEVC override integration."""
import argparse
from pathlib import Path
import re
import sys

COMMON = "android-shared/src/androidMain/kotlin/org/siloserver/silo/common/"
PHONE = "androidApp/src/androidMain/kotlin/org/siloserver/silo/android/"
TV = "androidTvApp/src/androidMain/kotlin/org/siloserver/silo/tv/"

# Intentionally fail closed when these integration points change. Review and
# update this guard alongside an intentional refactor, never auto-resolve it.
REQUIRED = {
    COMMON + "player/SiloPlayerFactory.kt": [
        "mimeType == MimeTypes.VIDEO_H265 -> infos.filter { it.hardwareAccelerated }.ifEmpty { infos }",
    ],
    COMMON + "player/MediaCodecCapabilitiesProbe.kt": [
        "var ignoreHevcLevelLimits: Boolean = PlayerSettingsStore.DEFAULT_IGNORE_HEVC_LEVEL_LIMITS",
        "fun probe(): ProbeResult = withHevcLevelLimitsIgnored( cached ?: synchronized(this) { cached ?: computeProbe().also { cached = it } }, ignoreHevcLevelLimits, )",
        '''internal fun withHevcLevelLimitsIgnored(result: ProbeResult, enabled: Boolean): ProbeResult {
            if (!enabled) return result
            return result.copy(videoDecodeCapabilities = result.videoDecodeCapabilities.map { capability ->
                if (capability.codec != "hevc") { capability } else { capability.copy(levels = emptyList()) }
            },)
        }''',
    ],
    COMMON + "settings/PlayerSettingsStore.kt": [
        "const val DEFAULT_IGNORE_HEVC_LEVEL_LIMITS = true",
        "val ignoreHevcLevelLimitsFlow: Flow<Boolean>",
        "suspend fun setIgnoreHevcLevelLimits(value: Boolean)",
    ],
    COMMON + "settings/AndroidPlayerSettingsStore.kt": [
        "override val ignoreHevcLevelLimitsFlow: Flow<Boolean> = profileScopedFlow(PlayerSettingsStore.DEFAULT_IGNORE_HEVC_LEVEL_LIMITS) { p, s -> p.intFor(s, PlaybackSettingsKeys.HevcLevelOverride, 1) > 0 }",
        "override suspend fun setIgnoreHevcLevelLimits(value: Boolean) = writeIntLocal(PlaybackSettingsKeys.HevcLevelOverride, if (value) 1 else 0)",
    ],
    COMMON + "settings/IgnoreHevcLevelLimitsBinder.kt": [
        "store.ignoreHevcLevelLimitsFlow.distinctUntilChanged().collect { enabled -> MediaCodecCapabilitiesProbe.ignoreHevcLevelLimits = enabled }",
    ],
    PHONE + "SiloApplication.kt": ["IgnoreHevcLevelLimitsBinder.start("],
    TV + "SiloTvApplication.kt": ["IgnoreHevcLevelLimitsBinder.start("],
    PHONE + "ui/screens/settings/PlaybackSettings.kt": [
        'label = "Ignore HEVC Level Limits", checked = ignoreHevcLevelLimits, onCheckedChange = onIgnoreHevcLevelLimitsChanged,',
    ],
    TV + "ui/screens/settings/TvSettingsScreen.kt": [
        'label = "Ignore HEVC Level Limits", checked = state.ignoreHevcLevelLimits, onCheckedChange = onIgnoreHevcLevelLimitsChanged,',
    ],
}


def compact(source):
    # Remove comments before matching so an obsolete, commented-out patch fails.
    source = re.sub(r"/\*.*?\*/|//[^\n]*", "", source, flags=re.S)
    return re.sub(r"\s+", "", source)


def check(root):
    failures = []
    for relative, fragments in REQUIRED.items():
        path = root / relative
        source = compact(path.read_text()) if path.is_file() else ""
        for fragment in fragments:
            if compact(fragment) not in source:
                failures.append(relative + ": " + fragment.splitlines()[0])
    return failures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    failures = check(args.root)
    if failures:
        print("HEVC override changed; review the upstream merge before updating main:", file=sys.stderr)
        for failure in failures:
            print("  " + failure, file=sys.stderr)
        return 1
    print("HEVC hardware decoder preference and level-limit override are intact.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
