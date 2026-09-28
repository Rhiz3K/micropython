# Reproduce the native TinyUSB USB-device regressions

These are host C unit tests with a mocked DCD, not an RP2350 USB-controller or
macOS-hub simulation. They prove the pinned queue-full defect and its repair;
they do not establish the cause of the historical hardware failures.

Sources: TinyUSB `b549ac1d84cbbe550c9590951e2290098b3fb16c`, upstream fix
`a0249ada9096365697340031a7b4a285beb18a2b`, plus the separate local test-only
[reset-queued-setup-test.patch](reset-queued-setup-test.patch). Do not apply `a52562b2...`.

The recorded tools were Ceedling 1.0.0, Ruby 4.0.7 and Apple clang 21.0.0
(`clang-2100.3.34.2`). No custom project configuration was used:
`test/unit-test/project.yml` matches the pinned source byte-for-byte. Its test
support configuration uses `OPT_OS_NONE`, default `OPT_MCU_NRF5X`, queue size
100 and default 16 events per task pass. DCD and MSC callbacks are mocked by
CMock. Prerequisite tools must already be available; no installation is part
of these commands.

From the root of a clean isolated TinyUSB copy at the pinned revision, first
apply only the upstream test hunk (set `usb_patch` to the absolute path of
[the official patch](../../../tinyusb-ep0-queue.patch)):

```sh
git apply --include=test/unit-test/test/device/usbd/test_usbd.c "$usb_patch"
cd test/unit-test
ceedling test:test_usbd
./_build/test/out/test_usbd/test_usbd.out -n test_usbd_setup_dropped_by_full_queue_recovers
```

Expected baseline: the named case fails, 1/1. The full file has 7 tests with 2
failures, because the queue-full failure leaves pending state which also
contaminates the following test. The isolated named case is the clean
before/after comparison.

Return to the TinyUSB root and apply only the production hunk:

```sh
git apply --include=src/device/usbd.c "$usb_patch"
cd test/unit-test
ceedling test:test_usbd
./_build/test/out/test_usbd/test_usbd.out -n test_usbd_setup_dropped_by_full_queue_recovers
```

Expected fixed result: 7/7, and the named case passes 1/1. Next, from the TinyUSB
root apply the local test-only patch (set `ordering_patch` to its path):

```sh
git apply "$ordering_patch"
cd test/unit-test
ceedling test:test_usbd
```

Expected result: 8/8. The new case queues BUS_RESET and then a valid
GET_DESCRIPTOR SETUP before the task drains the queue; the request must still
complete. The patched test file hash is
`e4b5733358ff18e4c5a411df021118f1e43a3f2db2c0ef8d15f0f8d4c72643bf`.

The exact recorded invocation used a private gem directory. With
`native_tests` set to the local `usb-unit-tests` directory and `native_ruby`
set to `/opt/homebrew/Library/Homebrew/vendor/portable-ruby/4.0.7/bin`, it was:

```sh
cd "$native_tests/patched/test/unit-test"
env GEM_HOME="$native_tests/gems" GEM_PATH="$native_tests/gems" \
  PATH="$native_ruby:$native_tests/gems/bin:$PATH" \
  "$native_ruby/ruby" "$native_tests/gems/bin/ceedling" test:test_usbd
```

Use `baseline` or `patched-ordering` instead of `patched` for the other saved
copies. The native executable's `-n` invocation needs no Ruby environment.
The original runs were supervised with a 100-second timeout. This note and
the extracted local patch were prepared from the existing logs and source;
no additional tests or hardware actions were performed during extraction.
