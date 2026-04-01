# Code Notes
## Detecting Load Completion
After injecting ```LOAD"*",8,1\rRUN\r``` into the keyboard buffer, the C64 goes through several phases:
1. BASIC prompt: $2D/$2E contains 0308 (the default BASIC variable pointer after reset)
2. The loader takes over: The first PRG on the disk loads and runs. It's typically pretty small and starts copying data into memory. While it does this, it writes to various memory locations including the area around $2D/$2E, so the value starts changing quickly.
3. Demo is running: Once the main demo code is fully loaded and running, memory stops being written to that area and $2D/$2E settles on a final value

```wait_for_load``` exploits this by:

1. Reading $2D/$2E immediately. The initial value should be 0308.
2. Polling every 0.5 seconds waiting for the value to change away from 0308 means the demo's loader has taken over.
3. Once it's changed, we poll for this value to stay the same for 4 consecutive reads (2 seconds). This means loading is done and the demo is running.
4. A that point it returns and the auto flip countdown starts.

The weakness is that some demos use custom loaders that either never touch $2D/$2E, or keep changing it throughout the demo's lifetime, which is why it won't work perfectly on every demo.
## Mount & Run
The C64 keyboard buffer lives at $0277–$0280 with 10 bytes maximum. The byte at $00C6 is the buffer count. The BASIC/kernal checks this on every interrupt and processes one keypress at a time.
We inject ```LOAD"*",8,1\rRUN\r``` in PETSCII:
```
4C 4F 41 44 22 2A 22 2C 38 2C  = LOAD"*",8,
31 0D 52 55 4E 0D              = 1\rRUN\r
```
This is 16 bytes which is too long for the 10-byte buffer. So we have to split it into two chunks:
Chunk 1 (10 bytes), and Chunk 2 (6 bytes):
```
PUT /v1/machine:writemem?address=0277&data=4C4F4144222A222C382C
PUT /v1/machine:writemem?address=00C6&data=0A   ← count = 10
Sleep 1 second — gives the C64 time to process the first chunk. The kernal reads the buffer on each interrupt (60 times/sec on NTSC, 50 on PAL), so 1 second is more than enough to drain all 10 bytes.
Chunk 2 (6 bytes):
PUT /v1/machine:writemem?address=0277&data=310D52554E0D
PUT /v1/machine:writemem?address=00C6&data=06   ← count = 6
```
The C64 sees ```LOAD"*",8,1``` followed by Return. After this executes. It returns to BASIC. ```RUN``` + Return is already in the buffer and this executes.
The C64 needs to be at a clean BASIC prompt before injecting. If something else is running, the keyboard buffer won't be processed. The reset guarantees a known state.
The writemem endpoint writes directly to C64 RAM via DMA over the cartridge bus, bypassing the CPU, so it works even while the C64 is busy doing something else.
## Flip Disk
When you search and select a multi-disk demo, GET /metadata/flipinfo is called from the Assembly64 API and filters by item ID. This returns a list of disk filenames with their play durations in seconds, eg
```
image1.d64 → 315s
image2.d64 → 308s
image3.d64 → 374s
image4.d64 → 158s
```
The length value means "this disk plays for N seconds before the next one is to be mounted"
Running
1. All disks are downloaded into memory
2. Disk 1 is uploaded to the Ultimate's /Temp/ folder and mounted
3. The C64 resets, BASIC boots, keyboard buffer is injected with ```LOAD"*",8,1``` then ```RUN```
4. wait_for_load polls $2D/$2E via DMA every 0.5 seconds — waits for it to change away from the BASIC reset value, then waits for it to stabilise — meaning the demo is fully loaded and running
5. Countdown starts from disk 1's length value (315s), updating the same line every second
6. This continues, using each disk's run time, mounting the next disk when it hits zero until there is nothing to flip to
Manual override
At any point during the countdown, pressing Enter flips immediately. Pressing q+Enter stops the whole sequence.
Local files
When you use ./assembly64.py run . in a directory, it looks for a flip file (232976-flip-info.txt, flip-info.txt, .lst, .vfl) and uses that for ordering and timing. Same logic, same countdown.
On download
If flip info is available from the API, a {item_id}-flip-info.txt is written alongside the downloaded files so run . works offline later.
