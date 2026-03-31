# Code Notes
## Mount & Run
The C64 keyboard buffer lives at $0277–$0280 with 10 bytes maximum. The byte at $00C6 is the buffer count. The BASIC/kernal checks this on every interrupt and processes one keypress at a time.
We inject ```LOAD"*",8,1\rRUN\r``` in PETSCII:
```
4C 4F 41 44 22 2A 22 2C 38 2C  = LOAD"*",8,
31 0D 52 55 4E 0D              = 1\rRUN\r
```
This is 16 bytes which is too long for the 10-byte buffer. So we have to split it into two chunks:
Chunk 1 (10 bytes):
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
