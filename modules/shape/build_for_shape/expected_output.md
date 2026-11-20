# Draw.NEXUS Shape API — Expected Outputs Specification

**Version:** 2.0  
**Status:** Proposed output contract  
**Scope:** Python Shape API, multiprocessing shared memory, packed transfer data, and C++ rendering bridge

---

## 1. Purpose

This document defines what the Draw.NEXUS Shape subsystem should return to Python callers and what it should publish to other processes and the renderer.

The design separates three representations because they have different jobs:

1. **Working Data** — editable Python-side shape state.
2. **Transfer Data (DGF)** — packed, versioned, optionally Zstandard-compressed bytes for inter-process transfer or compact storage.
3. **Active Runtime Data** — validated, uncompressed data in shared memory or renderer-owned memory, ready for frequent access.

These are representations of the same logical shape, not three independent sources of truth.

> **Source of truth:** Working Data is authoritative while a shape is being edited. Transfer Data is a transport/storage format. Active Runtime Data is a cache used by consumers. A cache can always be rebuilt from the authoritative data.

The output contract must not promise zero memory use, zero-copy in every situation, or a fixed FPS. Those depend on geometry size, compression, allocator behavior, platform, and renderer implementation.

---

# Part 2 — Public Python API Outputs

## 2.1 Return-value overview

| API | Return type | Meaning |
|---|---|---|
| `Draw.shape(...)` | `Shape` | Creates and registers a shape |
| `Draw.line(...)` | `Shape` or `Line` | Creates and registers a line; use one documented public class consistently |
| `Draw.shape.update(...)` | `Shape` | Mutates the shape and returns `self` |
| `Draw.shape.update(name, ...)` | `Shape` | Updates and returns the registered shape |
| `Draw.shape.list(name, data=...)` | `dict[str, Any]` | Returns requested inspection fields |
| `Draw.shape.query(keys=...)` | `dict[str, Any]` | Returns requested inspection fields |
| `Draw.shape.exists(name)` | `bool` | Whether the name is registered |
| `Draw.copy(...)` / `shape.copy(...)` | `Shape` | Creates a new shape with a new ID |
| `Draw.remove(names)` | `int` | Number of shapes removed |
| `Draw.shape.remove()` | `bool` | Whether this shape was removed |
| `Draw.shape.to_dict()` | `dict[str, Any]` | Explicit, human-readable serialization |

| `shape.publish(manager)` | `ShapeHandle` | Publishes/returns a lightweight reference to runtime data |
| `Draw.release_scene()` | `SceneFrameHandle` | Publishes a frame descriptor and scene version |

Do not let one method sometimes return a dictionary and sometimes return an unrelated raw buffer. Keep each method's return type stable. Legacy `release()` and `release_raw()` names, if retained, are deprecated aliases for `publish()` and `encode_transfer()` respectively.

## 2.1.1 Public API structure

Keep creation, registry operations, object operations, and transport operations separate. This prevents `Draw.shape` from becoming both a constructor and an overloaded service namespace.

| Layer | Canonical public operations | Responsibility |
|---|---|---|
| Creation | `Draw.shape(...)`, `Draw.line(...)` | Validate inputs, create/register, return `Shape` |
| Registry | `Draw.shapes.get(name)`, `.exists(name)`, `.update(name, ...)`, `.copy(name, new_name=...)`, `.remove(names)` | Named scene ownership and lookup |
| Instance | `shape.update(...)`, `.query(...)`, `.copy(...)`, `.remove()`, `.to_dict()` | Operations on one known shape |
| Transport | `shape.encode_transfer(...)`, `.publish(manager)`, `Draw.publish_scene(manager)` | Explicit serialization and cross-process publication |

For compatibility, `Draw.shape.update` and `Draw.shape.list` may delegate to `Draw.shapes` in v1, but new documentation and code should use `Draw.shapes`. The constructor remains `Draw.shape`; it must never return data from registry queries. `type` and `coordinate` are accepted compatibility names only; use `kind` and `coordinates` in new APIs if a future major version allows a rename.

## 2.2 Shape creation

```python
card = Draw.shape(
    name="card",
    type="rectangle",
    position=(0.0, 0.0),
    size=(100.0, 50.0),
    closed=True,
    z=0,
)
```

Expected result:

- Returns a `Shape` instance.
- Assigns a unique shape ID.
- Registers the shape under `"card"`.
- Creates its Working Data.
- Marks the initial geometry, transform, and metadata state as dirty.
- Does not need to allocate or compress a transfer packet until a consumer requests publication.

## 2.3 Query and inspection

```python
info = Draw.shape.list(
    "card",
    data=["size", "vertices", "z", "closed", "bounds", "position"],
)
```

Example result:

```python
{
    "name": "card",
    "position": (0.0, 0.0),
    "size": (100.0, 50.0),
    "vertices": 4,                 # count, not a duplicated vertex array
    "z": 0,
    "closed": True,
    "bounds": {
        "min_x": -50.0,
        "min_y": -25.0,
        "max_x": 50.0,
        "max_y": 25.0,
        "width": 100.0,
        "height": 50.0,
    },
    "origin": (0.0, 0.0),
    "parent_id": -1,
    "num_sub_shapes": 0,
}
```

Query methods should return only requested fields. A query for a vertex count must not copy the vertex array. If callers explicitly request vertices, return a documented copy or read-only view and make its lifetime clear.

## 2.4 Updates and dirty versions

```python
updated_card = card.update(
    position=(10.0, 20.0),
    size=(120.0, 60.0),
    z=2,
)
assert updated_card is card
```

The implementation should track independent versions/dirty states:

- `geometry_version`: vertices or indices changed.
- `transform_version`: position, rotation, scale, or origin changed.
- `metadata_version`: name, parent, z-order, flags, or other metadata changed.

A transform-only update must not rebuild or recompress geometry. Color, alignment, motion, and visibility changes are owned and published by their separate modules. A z-order-only update should update ordering metadata, not geometry.

## 2.5 Copy and remove

```python
card_clone = card.copy(new_name="card_clone")
removed_count = Draw.remove(["card", "button"])
removed = card_clone.remove()
```

A clone receives a new ID. Immutable geometry may be shared internally using reference counting or copy-on-write; the public API must still behave as if the clone is independent. Removing a shape from the registry does not immediately reclaim a shared allocation if a published frame or another shape still references it.

---

# Part 3 — Working Data Output

## 3.1 Purpose

Working Data is optimized for convenient Python editing and API behavior. It is not the representation to send repeatedly through multiprocessing queues or shared memory.

Example conceptual structure:

```python
{
    "id": 101,
    "name": "card",
    "type": "rectangle",
    "parent_id": -1,
    "closed": True,
    "z": 0,

    "transform": {
        "position": (0.0, 0.0),
        "scale": (1.0, 1.0),
        "rotation": 0.0,
        "origin": (0.0, 0.0),
    },

    "geometry": {
        "vertices": [...],         # one authoritative editable vertex collection
        "indices": [...],          # one authoritative index collection
    },

    "versions": {
        "geometry": 1,
        "transform": 1,
        "metadata": 1,
    },
}
```

This is an illustrative schema, not a requirement to use a Python dictionary internally. A `dataclass`, slots-based object, arrays, or another structure may be more memory-efficient. Avoid storing the same coordinates simultaneously as `vertices`, `coordinates`, and `perimeter` unless each is independently required.

## 3.2 `to_dict()` output

`to_dict()` is an explicit inspection/export operation. It may allocate Python lists and nested dictionaries, so it should not be called automatically in the frame loop.

Example:

```python
data = card.to_dict()
```

```python
{
    "id": 101,
    "name": "card",
    "type": "rectangle",
    "parent_id": -1,
    "closed": True,
    "z": 0,

    "transform": {
        "position": [0.0, 0.0],
        "scale": [1.0, 1.0],
        "rotation": 0.0,
        "origin": [0.0, 0.0],
    },


    "geometry": {
        "vertex_count": 4,
        "index_count": 6,
        "vertices": [
            -50.0,  25.0,  # Vertex 0: Top-left (Side 0 is top edge)
             50.0,  25.0,  # Vertex 1: Top-right
             50.0, -25.0,  # Vertex 2: Bottom-right
            -50.0, -25.0,  # Vertex 3: Bottom-left
        ],
        "indices": [0, 1, 2, 0, 2, 3],
    },

    "sub_shape_ids": [],
}
```

Derived values such as perimeter and bounds should be computed on request or cached carefully. Do not serialize duplicate derived geometry by default.

---

# Part 4 — Transfer Data: Packed DGF Packet

## 4.1 Purpose

Transfer Data is the stable, language-neutral binary representation used when geometry must cross a process boundary, be stored compactly, or be sent to another component.

The pipeline is:

```text
Working Data
    │
    ▼
Validate + pack into a defined binary layout
    │
    ▼
Optional lossless compression (Zstandard)
    │
    ▼
DGF packet bytes
    │
    ▼
Shared-memory slot or IPC transport
```

Packing and compression are different operations:

- **Packing** converts values into fixed-width binary fields and contiguous arrays.
- **Compression** losslessly reduces the byte count of the packed payload.
- The receiver validates the packet, decompresses if needed, then decodes the packed fields.

Compression is optional. It should be selected based on measured packet size and encode/decode cost. Do not recompress unchanged geometry on every frame.

## 4.2 DGF header

**DGF v1 header is exactly 24 bytes**, packed without implicit compiler padding. Fields are little-endian and the checksum is IEEE CRC-32 of the uncompressed payload. Python uses `struct.Struct("<4sHHBBHIII")`; C++ parses fields individually or uses a packed, size-asserted representation.

| Field | Type | Meaning |
|---|---|---|
| Offset | Field | Type | Meaning |
|---:|---|---|---|
| 0 | `magic` | `char[4]` | ASCII `DGF1` |
| 4 | `format_version` | `uint16` | `1` for this format |
| 6 | `header_size` | `uint16` | Always `24` for v1 |
| 8 | `compression` | `uint8` | `0 = none`, `1 = zstd` |
| 9 | `flags` | `uint8` | Must be zero; unknown bits reject the packet |
| 10 | `reserved` | `uint16` | Must be zero |
| 12 | `uncompressed_size` | `uint32` | Decoded payload size |
| 16 | `stored_size` | `uint32` | Bytes following the header |
| 20 | `checksum` | `uint32` | IEEE CRC-32 of uncompressed payload |

All multibyte values are little-endian. V1 rejects unknown versions, flags, compression values, non-zero reserved fields, stored payloads above 256 MiB, and decoded payloads above 512 MiB. Arrays begin on 4-byte boundaries and all offsets are measured from the payload start.

## 4.3 Payload layout

The uncompressed payload should contain fixed-width metadata followed by aligned arrays:

```text
DGF payload
+-----------------------------+
| Shape metadata              |
+-----------------------------+
| Transform fields            |
+-----------------------------+
| Geometry metadata fields    |
+-----------------------------+
| Vertex array: float32 XY    |
+-----------------------------+
| Alignment padding           |
+-----------------------------+
| Index array: uint32         |
+-----------------------------+
| Optional extension records |
+-----------------------------+
```

Use offsets and counts, not process-local pointers. For example:

```python
{
    "shape_id": 101,
    "parent_id": -1,
    "z": 0,
    "flags": 1,
    "vertex_offset": 64,        # byte offset from payload start
    "vertex_count": 4,          # XY pairs
    "index_offset": 96,          # byte offset from payload start
    "index_count": 6,
    "geometry_version": 1,
    "transform_version": 1,
}
```

The dictionary above illustrates the descriptor only; the actual packet stores these fields in fixed-width binary form.

## 4.4 Compression policy

Recommended default:

- Start with uncompressed packed data for small or frequently changing packets.
- Evaluate Zstandard for larger, mostly static geometry or when shared-memory capacity is the limiting factor.
- Consider a minimum payload threshold and a minimum expected savings threshold before compressing.
- Keep transform updates separate from geometry so they do not trigger geometry compression. Other modules publish their own component data.
- Cache the compressed packet by geometry version.
- Decompress once when a consumer activates or updates the geometry, not once per draw call.

Zstandard is a practical default when its dependency is acceptable. LZ4 may be preferable if extremely low latency matters more than compression ratio. ZIP/DEFLATE is useful for interoperability, but a ZIP archive adds container overhead; a zlib/DEFLATE stream is usually the more direct comparison.

The packet must remain lossless. Do not quantize or reduce float precision unless a separate explicitly lossy format is designed and accepted.

## 4.5 Transfer API contract

Recommended explicit API:

```python
packet = shape.encode_transfer(
    compression="zstd",       # "none" or "zstd"
    compression_level=3,
)
```

Example conceptual result:

```python
TransferPacket(
    format="DGF",
    version=1,
    compression="zstd",
    uncompressed_size=...,
    stored_size=...,
    checksum=...,
    data=bytes_or_readonly_buffer,
)
```

If the API exposes a `memoryview`, document who owns the backing memory and how long the view remains valid. A packet backed by a reusable scratch buffer must not be overwritten while a receiver is reading it.

---

# Part 5 — Active Runtime Data and Shared Memory

## 5.1 Purpose

Active Runtime Data is the consumer-ready representation. It is normally uncompressed so the renderer can access geometry without decompressing it repeatedly.

The shared-memory segment contains bytes and fixed-width records. It must not contain Python object pointers, `ctypes.c_void_p` values intended to be dereferenced by another process, or raw virtual addresses from the producer process.

## 5.2 Shared-memory descriptor

A process receives a small descriptor, not a large Python geometry object:

```python
ShapeHandle(
    segment_name="draw_geometry_0",
    allocation_id=42,
    generation=3,
    record_offset=4096,
    geometry_version=7,
)
```

The receiver attaches to the named shared-memory segment and resolves offsets relative to that mapping.

A handle should include enough information to detect stale references. `allocation_id` plus `generation` prevents an old handle from silently referring to a newly reused allocation.

## 5.3 Example fixed-width shape record

Illustrative C++ layout:

```cpp
#include <cstdint>

struct alignas(8) ShapeRecord {
    uint32_t shape_id;
    int32_t  parent_id;
    int32_t  z;
    uint32_t flags;

    uint64_t vertices_offset; // byte offset from geometry segment base
    uint64_t indices_offset;  // byte offset from geometry segment base

    uint32_t vertex_count;    // number of XY points
    uint32_t index_count;     // number of uint32 indices

    uint32_t geometry_version;
    uint32_t transform_index;

};
```

The exact ABI must be verified. Use `static_assert(sizeof(...))` and `static_assert(offsetof(...))` in C++, and matching Python tests. Do not assume compiler padding automatically matches a Python structure.

A process-local pointer may be created temporarily after attaching and resolving an offset, but it must never be stored as the cross-process reference.

## 5.4 Scene frame descriptor

```python
SceneFrameHandle(
    metadata_segment="draw_metadata_0",
    geometry_segment="draw_geometry_0",
    frame_slot=1,
    frame_id=9002,
    shape_count=250,
    scene_version=18,
)
```

The scene frame should reference a stable frame slot or immutable snapshot. It must not expose an array of pointers that become invalid when another process maps the segment at a different address.

## 5.5 Frame-slot ownership

Use an explicit slot state machine:

```text
FREE → WRITING → READY → READING → FREE
```

- Producer claims a `FREE` slot and changes it to `WRITING`.
- Producer writes all records and payload bytes, then publishes `READY` with the required synchronization.
- Consumer claims `READY`, marks it `READING`, and reads a stable snapshot.
- Consumer releases the slot to `FREE` when finished.

Use locks, semaphores, atomics, or another documented synchronization mechanism. Do not rely on the Python GIL for cross-process synchronization. Never overwrite a slot while a consumer is reading it.

A double- or triple-buffered design can reduce producer/consumer blocking, but the correct number of slots should be measured for the workload.

## 5.6 Allocation lifetime

- A central owner creates and unlinks shared-memory segments.
- Each process closes its own mapping.
- Reclaim an allocation only after no active frame or shape references it.
- Use reference counts, epochs, frame fences, or another explicit retirement mechanism.
- Do not reuse an allocation while a consumer may still read it.
- Validate every offset and count against the segment size before constructing a view.

---

# Part 6 — Renderer Bridge

## 6.1 Renderer-facing data

The renderer should consume a scene/frame descriptor plus offsets into shared memory. It should not receive producer-process pointers.

Conceptual C++ access:

```cpp
const auto* vertices =
    reinterpret_cast<const float*>(geometry_base + record.vertices_offset);

const auto* indices =
    reinterpret_cast<const uint32_t*>(geometry_base + record.indices_offset);

// Validate offsets/counts before this point.
// Upload or draw using the resolved arrays.
```

`geometry_base` is the local base address of the mapping in the renderer process. It can differ from the address used by Python.

## 6.2 Cython or ctypes

`ctypes` and Cython are both possible bridge technologies, but neither changes the shared-memory rules:

- For same-process calls, a pointer can be valid while its owner remains alive.
- Across processes, pass a segment name/handle and offsets, not a raw pointer.
- Keep all backing buffers alive for the full duration of a same-process native call.
- Specify integer widths, alignment, endianness, and ownership explicitly.

Do not claim that a Python `ctypes.Structure` containing pointers is automatically a safe cross-process format.

---

# Part 7 — Expected Method Behavior

| Operation | Working Data | Transfer Data | Active Runtime Data |
|---|---|---|---|
| Create shape | Create/editable state | Not required immediately | Allocate on publish/activation |
| Change vertices | Update geometry and version | Mark packet stale | Update geometry allocation |
| Change position/rotation/scale | Update transform/version | Geometry packet unchanged | Update transform record |
| Change color/stroke | No Shape change | Geometry packet unchanged | Color module updates its own record |
| Change z-order | Update metadata/version | Geometry packet unchanged | Update scene ordering |
| Publish to another process | Remains authoritative | Encode only changed data | Publish handle/frame descriptor |
| Consumer activation | No mutation | Validate/decode if needed | Store uncompressed runtime data |
| Draw frame | No `to_dict()` call | No per-frame compression | Read stable active snapshot |
| Remove shape | Remove registry entry | Retire packet reference | Reclaim only after readers release |

---

# Part 8 — Recommended Public API

Keep the API explicit so callers know whether they are inspecting, encoding, or publishing:

```python
# Developer inspection/export
debug_data = shape.to_dict()

# Produce a portable packed packet (compression optional)
packet = shape.encode_transfer(compression="zstd")

# Publish or retrieve a lightweight shared-memory reference
handle = shape.publish(shared_memory_manager)

# Publish a consistent scene snapshot
frame = Draw.publish_scene(shared_memory_manager)

# Consumer-side operations (names are illustrative)
runtime_shape = runtime_store.resolve(handle)
runtime_scene = runtime_store.resolve_frame(frame)
```

If existing method names must be retained:

- `release()` should return one documented lightweight handle/descriptor.
- `release_raw()` should return one documented packed packet or raw buffer, never an ambiguous mixture.
- `to_dict()` should remain the explicit human-readable export.
- `Draw.release_scene()` should return a frame descriptor, not a structure containing process-local pointers.

---

# Part 9 — Validation and Error Contract

Reject malformed or incompatible packets before using their contents.

At minimum validate:

1. Magic bytes and format version.
2. Header size and stored payload length.
3. Compression identifier and supported flags.
4. Maximum compressed and decompressed sizes.
5. Checksum after decompression.
6. All offsets, counts, alignments, and array extents.
7. Vertex and index counts against configured limits.
8. Every index is within the vertex range.
9. Shape IDs, generation values, and referenced parent/child IDs.
10. ABI/layout compatibility between Python and C++.

Use clear exceptions such as:

- `UnsupportedFormatVersion`
- `InvalidPacketHeader`
- `PacketSizeLimitExceeded`
- `ChecksumMismatch`
- `InvalidGeometryData`
- `StaleShapeHandle`
- `SharedMemoryAccessError`

Do not partially publish a frame if validation or writing fails. Leave the previous published frame intact.

---

# Part 10 — Performance and Memory Measurement

Benchmark the actual workload rather than promising a fixed reduction or frame rate.

Measure:

- Working Data memory per shape.
- Packed payload bytes.
- Compressed bytes and compression ratio.
- Encode and decode time.
- Shared-memory allocation and copy time.
- Number of geometry rebuilds per second.
- Peak resident memory across all processes.
- Frame publication latency.
- Renderer frame time and missed frames.
- Allocation fragmentation and time spent waiting for slots.

Test small, medium, and large scenes, including transform-only animation and frequent geometry changes. Compare compression modes (`none`, Zstandard, and optionally LZ4) on representative data.

---

# Final Architecture

```text
                 PYTHON SHAPE API
                        │
                        ▼
              ┌───────────────────┐
              │    WORKING DATA   │
              │ editable / source │
              └─────────┬─────────┘
                        │ geometry changed?
                        ▼
              ┌───────────────────┐
              │   PACK TO DGF     │
              │ fixed-width bytes │
              └─────────┬─────────┘
                        │ optional lossless compression
                        ▼
              ┌───────────────────┐
              │  TRANSFER DATA    │
              │ DGF + optional    │
              │ Zstandard         │
              └─────────┬─────────┘
                        │ IPC / shared-memory publication
                        ▼
              ┌───────────────────┐
              │ VALIDATE + DECODE │
              └─────────┬─────────┘
                        ▼
              ┌───────────────────┐
              │ ACTIVE RUNTIME    │
              │ uncompressed      │
              │ offsets + arrays  │
              └─────────┬─────────┘
                        ▼
                 C++ / GPU RENDERER
```

## Final rules

1. Working Data is the editable source of truth.
2. Transfer Data is a packed binary packet and may be losslessly compressed.
3. Active Runtime Data is the consumer-ready, usually uncompressed representation.
4. Use offsets and counts in shared memory; never persist process-local pointers as cross-process references.
5. Do not duplicate geometry in multiple Python lists without a clear need.
6. Do not rebuild or recompress geometry for transform/style-only changes.
7. Do not decompress geometry every draw call.
8. Keep allocations alive until every in-flight consumer has released them.
9. Validate packet sizes, versions, checksums, offsets, and indices before use.
10. Benchmark memory and latency on the target workload before selecting compression thresholds and buffer counts.
