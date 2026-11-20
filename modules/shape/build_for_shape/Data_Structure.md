# Draw Shape API — Summary of Working and Transfer Data Structures

## 1. Overview

The Shape API should maintain two distinct representations of shape data:

1. **Working Data Structure** — an editable, convenient representation used by the Python Shape API.
2. **Transfer Data Structure** — a compact binary representation prepared for inter-process transfer and optional lossless compression before storage in multiprocessing shared memory.

These structures serve different purposes. Working data prioritizes ease of use and modification; transfer data prioritizes compactness, predictable layout, and efficient communication.

A third representation may exist at runtime in the renderer:

3. **Active Runtime Data** — decompressed, directly readable geometry cached by the rendering process. This is not a replacement for the two main structures; it is a performance cache.

---

## 2. Working Data Structure

### Purpose

The working structure is the source-of-truth representation while a shape is being created, edited, transformed, copied, or removed.

It should be easy for Python code and users of the API to work with. It may use Python objects such as dictionaries, lists, tuples, and shape-specific classes.

### Example

```python
shape_data = {
    "shape_id": 12,
    "type": "rectangle",
    "vertices": [
        (0.0, 0.0),
        (100.0, 0.0),
        (100.0, 50.0),
        (0.0, 50.0),
    ],
    "indices": [0, 1, 2, 0, 2, 3],
    "position": (100.0, 200.0),
    "rotation": 0.0,
    "scale": (1.0, 1.0),
    "z": 2,
}
```

### Typical contents

- Shape identity and type.
- Editable vertices and indices.
- Position, rotation, scale, and origin.
- Parent/child relationships.
- Optional hitbox and collision settings.
- Dirty flags and geometry/transform/metadata version counters.

### Main uses

- Creating shapes through `Draw.shape()`.
- Updating geometry and appearance.
- Applying transforms.
- Copying and removing shapes.
- Building and editing shape hierarchies.
- Generating optional derived data such as hitboxes or coordinate maps.

### Design rules

- Keep this representation convenient, not optimized for inter-process transfer.
- Track changes with separate geometry, transform, and ordering versions. Color, alignment, motion, and visibility have independent component versions outside Shape.
- Do not create transfer packets on every property access.
- Avoid keeping duplicate derived data unless it is frequently used.
- Generate debug dictionaries and expanded exports only when explicitly requested.

### Advantages

- Easy to inspect and debug.
- Convenient to modify.
- Natural fit for the public Python API.
- Supports flexible shape types and optional properties.

### Disadvantages

- Python lists, tuples, dictionaries, and numeric objects have relatively high memory overhead.
- Not a stable binary ABI for C++.
- Sending it through multiprocessing queues requires serialization and copying.
- Nested objects can create duplicate data and expensive traversal.

---

## 3. Transfer Data Structure

### Purpose

The transfer structure is a packed, fixed-layout binary representation generated from working data. It is designed for efficient storage, validation, and communication between processes.

It should contain only the fields needed by the receiving process. It should not be a second editable Python object graph.

### DGF v1 (Draw Geometry Format)

Use the versioned binary packet format defined in `expected_output_rewritten.md`. The v1 header is exactly 24 bytes, little-endian, with IEEE CRC-32 of the uncompressed payload. This summary does not define a second packet layout.

### Example packet layout

```text
+--------------------------------+
| DGF HEADER                     |
+--------------------------------+
| Magic: 4 bytes ("DGF1")        |
| Format version: uint16 (= 1)   |
| Header size: uint16 (= 24)     |
| Compression method: uint8      |
| Flags: uint8                   |
| Reserved: uint16 (= 0)         |
| Uncompressed size: uint32      |
| Stored payload size: uint32    |
| Checksum: uint32 (IEEE CRC-32) |
+--------------------------------+
| PAYLOAD                        |
+--------------------------------+
| Shape metadata                 |
| Vertex data                    |
| Index data                     |
| Optional sections              |
+--------------------------------+
```

The uncompressed payload can contain:

```text
+--------------------------------+
| SHAPE RECORD                   |
| Shape ID                       |
| Geometry version               |
| Vertex count                   |
| Index count                    |
| Transform references           |
+--------------------------------+
| VERTEX DATA                    |
| float32 x, y                   |
| float32 x, y                   |
| ...                            |
+--------------------------------+
| INDEX DATA                     |
| uint32 indices                 |
| ...                            |
+--------------------------------+
| OPTIONAL SECTIONS              |
| Hitbox data                    |
| Sub-shape IDs/references       |
+--------------------------------+
```

Header widths, byte order, maximum packet sizes, and offsets are normative in `expected_output_rewritten.md`. Vertex arrays and indices are 4-byte aligned; Python/C++ conformance tests must encode and decode the same fixtures.

### Compression

Use **Zstandard (Zstd)** as the preferred optional lossless compressor.

- Binary packing converts Python objects into a compact, predictable representation.
- Zstd then reduces the size of that binary representation.
- Compression is lossless: decompression reconstructs the exact packed bytes.
- Compression does not itself make data directly renderable; the consumer must decompress before interpreting the payload.

Do not assume compression always saves memory. Small or frequently changing packets may be faster and smaller overall when left uncompressed. Measure the result and use a configurable threshold.

### Main uses

- Transferring shape data between multiprocessing processes.
- Storing static or infrequently changing geometry compactly.
- Caching packed geometry.
- Persisting or exporting versioned geometry packets.
- Sending small packet descriptors through multiprocessing queues while the bytes reside in shared memory.

### Advantages

- Compact compared with Python object graphs.
- Predictable, versioned layout.
- Easier to validate across Python and C++.
- Can be compressed losslessly.
- Suitable for shared-memory storage.

### Disadvantages

- Requires encoding and decoding.
- Compressed data must be decompressed before normal geometry access.
- Needs strict format/version/size validation.
- Compression can add CPU time and temporary memory.
- It is less convenient to edit directly.

---

## 4. Runtime Active Data (Renderer Cache)

The renderer may maintain a third, uncompressed representation for geometry it is actively using.

### Purpose

Avoid decompressing the same geometry every frame.

### Typical contents

- Decompressed vertex and index buffers.
- GPU upload state or GPU buffer handles.
- Geometry version currently loaded.
- References to source packet/allocation IDs.

### Main uses

- Drawing active shapes.
- Reusing geometry across frames.
- Uploading changed geometry to the GPU only when its version changes.

This cache is an optimization. It should have a memory budget and eviction policy. It must not become an uncontrolled duplicate of all compressed geometry.

---

## 5. Comparison

| Property | Working Data | Transfer Data | Active Runtime Data |
|---|---|---|---|
| Main purpose | Editing | Communication/storage | Rendering |
| Representation | Python objects | Packed binary, optionally compressed | Uncompressed buffers |
| Human-readable | Usually | No | No |
| Easy to modify | Yes | No | Usually no |
| Lossless compression | Not normally | Optional Zstd | Normally no |
| Shared-memory suitable | Not directly | Yes | Yes, if needed |
| C++ ABI | No | Yes, when explicitly specified | Native renderer layout |
| Typical lifetime | Shape editing lifetime | Until transfer/cache eviction | While actively used |

---

## 6. Recommended data flow

```text
             SHAPE CREATION / EDITING
                       |
                       v
              WORKING DATA STRUCTURE
               (Python objects)
                       |
              geometry changed?
                       |
                       v
                BINARY ENCODER
                       |
                       v
              TRANSFER DATA (DGF)
                       |
             compression worthwhile?
                 /           \
               yes            no
                |              |
                v              |
          ZSTD COMPRESS        |
                |              |
                +-------+------+
                        |
                        v
              SHARED MEMORY STORAGE
                        |
             Queue sends small handle
                        |
                        v
                RENDERER PROCESS
                        |
              compressed packet?
                 /           \
               yes            no
                |              |
                v              |
          ZSTD DECOMPRESS      |
                |              |
                +-------+------+
                        |
                        v
              ACTIVE RUNTIME DATA
                        |
                        v
                  GPU / DRAW
```

---

## 7. When each representation should be updated

| Operation | Working Data | Transfer Data | Active Runtime Data |
|---|---|---|---|
| Create shape | Create | Encode when published | Create/load when needed |
| Change vertices | Update | Mark stale; re-encode | Refresh on new version |
| Change indices | Update | Mark stale; re-encode | Refresh on new version |
| Change position | Update transform | Update small transform record | Update transform |
| Change rotation/scale | Update transform | Update small transform record | Update transform |
| Change color | No Shape update | No Shape packet update | Color module updates its component |
| Draw another frame | Reuse | Reuse | Reuse |
| Remove shape | Remove from registry | Retire packet when safe | Evict when no longer in use |

The key optimization is to keep geometry and frequently changing transforms separate. Moving a shape should not require recompressing its vertices and indices; non-geometry modules publish independently.

---

## 8. Recommended API surface

```python
# Create and edit the working representation.
shape = Draw.shape(
    type="rectangle",
    size=(100, 50),
)

shape.update(position=(100, 200))

# Encode only when geometry or transferable data changes.
packet = Draw.codec.encode(shape)

# Optionally compress the packed bytes.
compressed_packet = Draw.codec.compress(packet)

# Store the packet in shared memory.
handle = Draw.memory.write(compressed_packet)

# Send only the handle / allocation ID / version to the renderer.
Draw.renderer.submit(handle)

# Explicit debug/export operation; not part of the hot path.
debug_data = shape.to_dict()
```

Suggested modules:

```text
Draw/
├── shape/
│   ├── shape.py
│   ├── geometry.py
│   └── transform.py
├── codec/
│   ├── format.py
│   ├── encoder.py
│   ├── decoder.py
│   ├── compressor.py
│   └── decompressor.py
├── memory/
│   ├── manager.py
│   ├── allocator.py
│   └── buffer.py
└── renderer/
    └── bridge.py
```

---

## 9. Shared-memory and multiprocessing rules

1. Store bytes, fixed-width integers, floats, and offsets in shared memory—not Python object pointers.
2. Processes should attach to shared-memory segments by name.
3. Store offsets relative to the segment base; never store a process-local pointer as a cross-process address.
4. Send small handles and version numbers through multiprocessing queues, not geometry payloads.
5. Do not overwrite a packet while a consumer is reading it.
6. Retire allocations only after all in-flight frames have released their references.
7. The designated owner unlinks each shared-memory segment once; each process closes its own mapping.
8. Validate packet magic, version, lengths, checksum, and maximum decompressed size before using data.
9. Avoid recompressing unchanged geometry.
10. Measure compression ratio, encode/decode time, peak memory, and frame latency.

A useful additional rule: use compressed shared-memory storage for static or infrequently updated data, and an uncompressed active buffer for data the renderer needs to access frequently. This avoids paying decompression cost on every draw.

---

## 10. Final recommendation

Use the following division of responsibility:

- **Working Data:** the authoritative, editable representation owned by the Shape API.
- **Transfer Data (DGF):** a versioned packed binary representation, optionally compressed with Zstandard, used for inter-process transfer and compact storage.
- **Active Runtime Data:** an uncompressed renderer-side cache used to avoid repeated decompression and support efficient drawing.

Do not treat ZIP/Zstd compression as a substitute for binary packing. First pack the data into a well-defined binary layout, then optionally compress it. Also, do not compress every frame by default: use dirty/version tracking, size thresholds, and measurements to decide when compression is worthwhile.

This separation keeps the public Shape API convenient while allowing the multiprocessing and rendering layers to optimize memory usage independently.


# PART 9 — Release Pipeline (Zero External Dependencies)

## Zero-Dependency Philosophy (No NumPy)
> **Constraint:** Introducing NumPy is prohibited because it adds heavy binary dependencies, inflates library size, and risks environment conflicts.
> The Shape system uses **pure Python standard types** (`list`, `tuple`, `float`, `int`) and standard library buffer interfaces (`array.array` / `ctypes`).

## Public export, transfer, and publication

The public API uses one stable return type per operation:

```python
debug_data = card.to_dict()                         # human-readable, copied export
packet = card.encode_transfer(compression="none")  # DGF TransferPacket
handle = card.publish(shared_memory_manager)        # ShapeHandle
```

`release()` and `release_raw()` are not public v1 API names because their result types were ambiguous. If retained for migration, `release()` returns only `ShapeHandle` and `release_raw()` returns only `TransferPacket`.

---

# PART 10 — Renderer Bridge

For direct C++ interop with the Render Engine (`d:\draw3\rander_engin\c++files\`):

```python
packet = card.encode_transfer(compression="none")
```

The renderer obtains a process-local view only after validating a packet or resolving a `ShapeHandle`. Python buffers can be contiguous, but a C++ pointer is process-local and its lifetime must be owned by the caller; pointers are never transferred between processes.

---
