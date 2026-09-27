#!/usr/bin/env bash
# Rebuild the reviewed baseline and patch in a new, isolated clone.
# Linux x86_64 prerequisites: git, curl, tar/xz, Python 3 + venv, GNU Make,
# host C/C++ compiler, pkg-config. This script never accesses a device.
# Usage: ./reproduce.sh /absolute/path/to/new-build-directory
# Optional: JOBS=4 ARM_TOOLCHAIN_ARCHIVE=/path/to/verified-archive.tar.xz
set -euo pipefail

readonly base_sha=09f5bb447504a058376c62fe991b3613531837e6
readonly sdk_sha=98a542c1a62fb549ffb5d66a3e5892b06276b670
readonly picotool_sha=6f6458d792b93685a11423b244a585eaa99eafcf
readonly toolchain_name=arm-gnu-toolchain-14.3.rel1-x86_64-arm-none-eabi
readonly toolchain_sha=8f6903f8ceb084d9227b9ef991490413014d991874a1e34074443c2a72b14dbd
readonly toolchain_url="https://developer.arm.com/-/media/Files/downloads/gnu/14.3.rel1/binrel/${toolchain_name}.tar.xz"
readonly bundle_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

if [[ $# -ne 1 || -e "$1" ]]; then
    printf 'Usage: %s /path/to/NEW-build-directory\n' "$0" >&2
    printf 'The destination must not already exist. No existing tree is deleted.\n' >&2
    exit 2
fi
if [[ ! -s "${bundle_dir}/firmware.patch" ]]; then
    printf 'Missing firmware.patch beside reproduce.sh\n' >&2
    exit 2
fi
case "$(uname -sm)" in
    'Linux x86_64') ;;
    *) printf 'This recipe pins the Linux x86_64 ARM toolchain archive.\n' >&2; exit 2 ;;
esac

mkdir -p -- "$1"
readonly build_root="$(cd -- "$1" && pwd)"
readonly source_dir="${build_root}/micropython"
readonly jobs="${JOBS:-4}"
mkdir -p "${build_root}/logs" "${build_root}/artifacts"
exec > >(tee "${build_root}/logs/reproduce.log") 2>&1

# Keep the firmware build date fixed. 1790294400 is 2026-09-25 00:00:00 UTC.
export SOURCE_DATE_EPOCH=1790294400
export TZ=UTC
export LC_ALL=C

if [[ -n "${ARM_TOOLCHAIN_ARCHIVE:-}" ]]; then
    archive="$(realpath -- "$ARM_TOOLCHAIN_ARCHIVE")"
else
    archive="${build_root}/${toolchain_name}.tar.xz"
    curl --fail --location --retry 3 --output "$archive" "$toolchain_url"
fi
printf '%s  %s\n' "$toolchain_sha" "$archive" | sha256sum --check -
tar -xf "$archive" -C "$build_root"

python3 -m venv "${build_root}/venv"
"${build_root}/venv/bin/python" -m pip install 'cmake==4.4.3'
export PATH="${build_root}/venv/bin:${build_root}/${toolchain_name}/bin:${PATH}"
export PICO_TOOLCHAIN_PATH="${build_root}/${toolchain_name}"

# Full clone (with tags) keeps makeversionhdr's git-derived version reproducible.
git clone https://github.com/micropython/micropython.git "$source_dir"
git -C "$source_dir" checkout --detach "$base_sha"
export PICO_SDK_PATH="${source_dir}/lib/pico-sdk"
# The SDK normally fetches picotool tag 2.3.0. Pin its exact source commit.
# Use an environment variable so the rp2 Makefile appends its board arguments.
unset PICOTOOL_FETCH_FROM_GIT_PATH
export CMAKE_ARGS="-DPICOTOOL_GIT_BRANCH=${picotool_sha} -DPICOTOOL_FORCE_FETCH_FROM_GIT=1 -DCMAKE_BUILD_TYPE=MinSizeRel"

{
    uname -a
    cat /etc/os-release
    git --version
    python --version
    cmake --version
    make --version
    arm-none-eabi-gcc --version
    cc --version
    printf 'SOURCE_DATE_EPOCH=%s\n' "$SOURCE_DATE_EPOCH"
    printf 'MicroPython=%s\nPico SDK=%s\nPicotool=%s\n' "$base_sha" "$sdk_sha" "$picotool_sha"
    printf 'Toolchain archive SHA256=%s\n' "$toolchain_sha"
} > "${build_root}/logs/environment.txt"

make -C "${source_dir}/ports/rp2" BOARD=RPI_PICO2_W submodules \
    2>&1 | tee "${build_root}/logs/submodules.log"
[[ "$(git -C "${source_dir}/lib/pico-sdk" rev-parse HEAD)" == "$sdk_sha" ]]
git -C "$source_dir" submodule status --recursive > "${build_root}/logs/submodule-revisions.txt"
make -C "${source_dir}/mpy-cross" -j"$jobs" \
    2>&1 | tee "${build_root}/logs/mpy-cross.log"

build_board() {
    local phase="$1" board="$2"
    local relative_build="build-${phase}-${board}"
    local board_dir="${source_dir}/ports/rp2/${relative_build}"
    make -C "${source_dir}/ports/rp2" BOARD="$board" BUILD="$relative_build" -j"$jobs" \
        2>&1 | tee "${build_root}/logs/${phase}-${board}.log"
    [[ "$(git -C "${board_dir}/_deps/picotool-src" rev-parse HEAD)" == "$picotool_sha" ]]
    cp "${board_dir}/firmware.uf2" "${build_root}/artifacts/${phase}-${board}.uf2"
    cp "${board_dir}/firmware.elf" "${build_root}/artifacts/${phase}-${board}.elf"
    arm-none-eabi-size "${board_dir}/firmware.elf" \
        > "${build_root}/logs/${phase}-${board}-size.txt"
}

# Baseline comes first. No patch has been applied at this point.
build_board baseline RPI_PICO2_W
build_board baseline RPI_PICO

git -C "$source_dir" apply --check "${bundle_dir}/firmware.patch"
git -C "$source_dir" apply "${bundle_dir}/firmware.patch"
git -C "$source_dir" diff --check
git -C "$source_dir" diff --stat > "${build_root}/logs/firmware-diff-stat.txt"

build_board patched RPI_PICO2_W
build_board patched RPI_PICO2
build_board patched RPI_PICO

# Tests are a separate review patch and do not contribute frozen firmware code.
if [[ -s "${bundle_dir}/tests.patch" ]]; then
    git -C "$source_dir" apply --check "${bundle_dir}/tests.patch"
    git -C "$source_dir" apply "${bundle_dir}/tests.patch"
fi
(
    cd "${build_root}/artifacts"
    sha256sum ./*.uf2 ./*.elf > SHA256SUMS
)
printf 'Built artifacts: %s\n' "${build_root}/artifacts"
printf 'Build logs: %s\n' "${build_root}/logs"
printf 'No flashing, hardware tests, power measurements or RISC-V build were performed.\n'
