---
title: "CS Roadmap (3) — Hash Tables: Conditions and Limits of O(1) Lookup"
lang: en
date: 2026-03-14 10:00:00 +0900
categories: [AI, CS]
tags: [Hash Table, Hash Function, Open Addressing, Chaining, Robin Hood Hashing, Cache, Collision, CS Fundamentals]
difficulty: intermediate
toc: true

math: true
image: /assets/img/og/cs.png
tldr:
  - "Hash tables achieve O(1) lookups by converting keys to integers (hash function) and mapping them to array indices — the quality of the hash function determines overall performance"
  - "Two collision resolution strategies — chaining is simple to implement but causes cache misses due to pointer chasing, while open addressing (especially Linear Probing) is cache-friendly through sequential memory access"
  - "For Linear Probing, when the load factor (α) exceeds 0.7, collision probability surges and performance degrades from O(1) to O(n) — the tolerable load factor varies depending on the collision resolution strategy"
  - "Robin Hood Hashing uses a 'steal from the rich, give to the poor' strategy to reduce variance in probe distances, serving as the foundation for Rust HashMap and modern high-performance hash tables"
---

## Introduction

> This article is the 3rd installment of the **CS Roadmap** series.

"Find the value for this key."

This is the most frequent question in programming. Looking up stats by monster ID, retrieving configuration values by string key, finding tile data by coordinates. The data structure that answers this question in **O(1)** is the hash table.

In [Part 1](/posts/ArrayAndLinkedList/), we saw how arrays provide O(1) access by index. The core idea of hash tables is simple: **convert an arbitrary key into an array index**, and you can leverage the array's O(1) access directly. The function that performs this conversion is the **hash function**.

A simple idea, but the devil is in the details. What happens when different keys convert to the same index (**collision**)? How do you design a hash function? What happens when the array is full? The answers to these questions are the essence of hash tables.

> **Language-specific implementations such as C# Dictionary and Java HashMap** are covered in a separate post ([C# Data Structures - Dictionary and SortedList](/posts/CsharpDS01/)). This article focuses on **language-agnostic fundamental principles of hash tables**.

Upcoming series structure:

| Part | Topic | Core Question |
| --- | --- | --- |
| **Part 3 (this article)** | Hash Tables | How is O(1) possible, and what is its price? |
| **Part 4** | Trees | Why do we need BST, Red-Black Tree, B-Tree? |
| **Part 5** | Graphs | What are the principles of traversal, shortest path, and topological sort? |
| **Part 6** | Memory Management | What are the tradeoffs of stack/heap, GC, and manual memory management? |

---

## Part 1: Hash Functions — The Art of Converting Keys to Numbers

### Basic Structure of a Hash Table

A hash table consists of three elements:

1. **Array (bucket array)**: A fixed-size array that stores data
2. **Hash function**: Converts key → integer
3. **Collision resolution strategy**: Handling when two keys point to the same index

```
Key "MOB_001" → hash("MOB_001") = 374821 → 374821 % 8 = 5 → bucket[5]

┌───────┬───────┬───────┬───────┬───────┬───────────────┬───────┬───────┐
│ [0]   │ [1]   │ [2]   │ [3]   │ [4]   │ [5]           │ [6]   │ [7]   │
│ empty │ empty │ empty │ empty │ empty │ MOB_001:Goblin │ empty │ empty │
└───────┴───────┴───────┴───────┴───────┴───────────────┴───────┴───────┘
```

Lookups follow the same path: key → hash function → index → array access. Since array access is O(1), **if the hash function is O(1)**, the entire operation is O(1).

Strictly speaking, hash table O(1) rests on the assumption that **hash computation cost and key equality comparison cost are both constant**. For integer keys this holds, but for string keys, hash computation is O(L) and comparison is also O(L), so it's effectively O(L). We'll revisit this point later.

### The Hash-Equality Contract

For a hash table to function correctly, there is a **contract that must be upheld** between the hash function and equality comparison:

> **If `a == b`, then `hash(a) == hash(b)` must hold.**

The converse need not be true — `hash(a) == hash(b)` but `a != b` is simply a collision. But violating the forward rule breaks the hash table. The same key gets stored in different buckets, making lookups fail.

A common mistake in practice:

```csharp
// Dangerous: using a mutable object as a key
var enemy = new Enemy { Id = 1, Hp = 100 };
dict[enemy] = "goblin";

enemy.Hp = 50;  // Key object's state changed!
dict[enemy];    // KeyNotFoundException! Hash value changed, probing a different bucket
```

Therefore, **hash table keys should be immutable**. In C#, if you override `GetHashCode()`, you must also override `Equals()`. In Java, if you override `hashCode()`, you must also override `equals()`. Bloch's *Effective Java* Item 11 explains this principle in detail.

Lesson for game development: it's safe to use **immutable identifiers** like monster IDs and item IDs as keys. Using game objects themselves as keys risks breaking the hash table when their state changes.

### Conditions for a Good Hash Function

Knuth summarized the key conditions for hash functions in *The Art of Computer Programming Vol. 3*:

1. **Deterministic**: The same key must always return the same hash value
2. **Uniform Distribution**: Hash values should be evenly spread across the possible range
3. **Efficient Computation**: The hash function itself must be fast — O(1) or proportional to key length

Condition 2 is the most critical. If hash values cluster on one side, collisions concentrate and performance degrades to O(n).

### Integer Key Hashing: Division and Multiplication Methods

**Division Method**:

$$h(k) = k \mod m$$

The most intuitive approach. The remainder of dividing key k by table size m. However, the choice of m matters:

- **m as a power of 2 is dangerous.** $k \mod 2^p$ uses only the lower p bits of k. All information in the upper bits is discarded.
- **m as a prime number is good.** It produces an even distribution regardless of the key's bit pattern. This is why .NET `Dictionary` uses prime-sized tables.

**Multiplication Method**:

$$h(k) = \lfloor m \cdot (k \cdot A \mod 1) \rfloor, \quad 0 < A < 1$$

Knuth's suggested value for A is **the reciprocal of the golden ratio** $A = \frac{\sqrt{5} - 1}{2} \approx 0.6180339887$. This value is theoretically the constant that "spreads most evenly" in a one-dimensional uniform distribution.

The advantage of the multiplication method is that m can be chosen freely. In particular, **choosing m as a power of 2** allows the modular operation to be replaced with a **bitmask (AND)**, making it fast. For example, `hash % 16` is identical to `hash & 0xF` — the same principle as the `& (capacity - 1)` trick from Part 2's ring buffer.

> **Let's pause and address this**
>
> **Q. Why exactly is power-of-2 modular dangerous?**
>
> Suppose game object IDs are multiples of 8 (common due to memory alignment). For $k = 8, 16, 24, 32, ...$, $k \mod 16$ is always 0 or 8. All data clusters in just 2 out of 16 buckets. With prime m=17: $8 \mod 17 = 8$, $16 \mod 17 = 16$, $24 \mod 17 = 7$, $32 \mod 17 = 15$ — evenly distributed.
>
> However, like Java `HashMap`, if you **additionally perturb the hash value**, power-of-2 tables can be used safely. Java XORs the upper 16 bits of the hash value into the lower 16 bits to mix them.

### String Key Hashing

Strings are variable-length, so each character is accumulated to produce a hash. The most widely used approach:

**Polynomial Rolling Hash**:

$$h(s) = s[0] \cdot p^{n-1} + s[1] \cdot p^{n-2} + \cdots + s[n-1] \cdot p^0$$

Where p is a prime (typically 31 or 37). Java's `String.hashCode()` uses this approach:

```java
// Java String.hashCode() — a slightly modified polynomial hash
int hash = 0;
for (int i = 0; i < str.length(); i++) {
    hash = 31 * hash + str.charAt(i);
}
```

Why 31? Since $31 = 2^5 - 1$, the compiler can optimize `31 * x` as `(x << 5) - x`. After Bloch recommended this in *Effective Java*, it became the de facto standard.

More modern hash functions:

| Hash Function | Speed | Quality | Use Cases |
| --- | --- | --- | --- |
| **FNV-1a** | Fast | Fair | General purpose, simple implementation |
| **MurmurHash3** | Very fast | Good | General hash tables, Cassandra, Elasticsearch |
| **xxHash** | Extremely fast | Good | Checksums, data processing |
| **SipHash** | Moderate | Good + DoS defense | Rust HashMap, Python dict, Redis, Ruby |
| **wyhash** | Extremely fast | Good | Go map (1.17~1.23) |

Common uses of string keys in game development: resource paths, animation names, event names. **String hash computation is proportional to string length (O(L))**, so in places called every frame, you should consider **caching the hash** or **string interning**.

---

## Part 2: Collision Resolution — Chaining

### The Pigeonhole Principle

No matter how good the hash function is, collisions are **inevitable**.

**Pigeonhole Principle**: When placing n pigeons into m holes, if $n > m$, at least one hole must contain two or more pigeons.

The possible values for keys are practically infinite (strings alone are unlimited), but array size m is finite. Therefore, different keys mapping to the same index — collisions — cannot be avoided.

The **Birthday Paradox** demonstrates this even more dramatically. With just 23 keys in 365 buckets, the probability of collision **exceeds 50%**. In general, inserting $\sqrt{m}$ keys into m buckets gives approximately a 50% chance of collision.

### Separate Chaining

The most intuitive collision resolution method. Elements mapped to the same index are linked using a **linked list (or another data structure)**.

```
buckets:
[0] → (K="Orc", V=30) → NULL
[1] → NULL
[2] → (K="Goblin", V=10) → (K="Slime", V=5) → NULL
[3] → (K="Dragon", V=100) → NULL
[4] → NULL
```

To find "Slime" in bucket 2: traverse the list in bucket 2, comparing keys.

![Separate Chaining — Collision Resolution](/assets/img/post/cs/excalidraw-01-chaining-en.png)

**Time Complexity**:

- Average: O(1 + α), where α = n/m (load factor)
- Worst case: O(n) — when all keys cluster in one bucket

**Advantages**:
- Simple to implement
- Works even when load factor exceeds 1
- Deletion is straightforward (remove a node from the linked list)

**Disadvantage — Cache Performance**:

Let's apply the lesson from Part 1 here. Each node in chaining is a **separate heap allocation**. Since nodes are scattered across memory, every time you follow a chain, there's a high probability of a **cache miss**.

```
Memory space:
0x1000: [bucket array]
  ...
0x3040: [Node: Goblin]  ← cache miss
  ...
0x7820: [Node: Slime]   ← another cache miss
```

This is the answer to "why is it slow despite being O(1)?" The cost of cache misses is hidden in Big-O's constant factor.

### Improving Chaining: In-Array Chaining

.NET `Dictionary` solves this problem cleverly. Instead of separate nodes, it **chains using `next` indices within the entries array**:

```
entries[] (contiguous array):
[0] hash=9284 next=-1 Key="Goblin"  Val=10
[1] hash=3507 next=-1 Key="Slime"   Val=5
[2] hash=3500 next=1  Key="Orc"     Val=30    ← next=1 points to [1]
[3] hash=7423 next=-1 Key="Dragon"  Val=100

buckets[]:
[0] → 0    // entries[0]
[2] → 2    // entries[2] → entries[2].next=1 → entries[1]
[3] → 3
```

Since all entries are in **a single contiguous array**, even following chains within the same bucket means moving within the array, **preserving cache locality**. This is fundamentally different from traditional linked-list chaining.

---

## Part 3: Collision Resolution — Open Addressing

### The Basic Idea of Open Addressing

A completely different approach from chaining: **find an empty slot within the array itself, without any external structure.**

When a collision occurs, the next empty slot is found according to a predetermined **probing sequence**. All data exists within a single array.

### Linear Probing — The Simplest and Most Cache-Friendly

When a collision occurs, check **the next slot, then the next, ...** in order.

$$h(k, i) = (h(k) + i) \mod m, \quad i = 0, 1, 2, \ldots$$

```
Insertion process: h("Orc")=2, h("Slime")=2 (collision!), h("Troll")=3

Step 1: "Orc" → index 2 (empty) → insert
[  ] [  ] [Orc] [  ] [  ] [  ] [  ] [  ]

Step 2: "Slime" → index 2 (collision!) → 3 (empty) → insert
[  ] [  ] [Orc] [Slime] [  ] [  ] [  ] [  ]

Step 3: "Troll" → index 3 (collision!) → 4 (empty) → insert
[  ] [  ] [Orc] [Slime] [Troll] [  ] [  ] [  ]
```

**Excellent cache performance.** Probing accesses consecutive memory sequentially, maximizing the benefit of **spatial locality** as we learned in Part 1. Since multiple slots fit in a single cache line (64 bytes), most probing resolves within L1 cache.

**Clustering Problem**:

This is linear probing's weakness. When collisions occur, data piles up next to existing data, and the piled data causes more collisions, growing the cluster. This is called **Primary Clustering**.

```
Cluster formation process:
[  ][  ][██][██][██][██][  ][  ]  ← 4-slot cluster
                                    Any key hashing near here joins this cluster
[  ][  ][██][██][██][██][██][  ]  ← Grows to 5 slots
```

Knuth analyzed the average probe length of linear probing in TAOCP Vol. 3:

**Successful search (key exists)**:

$$E[\text{probes}] = \frac{1}{2}\left(1 + \frac{1}{1 - \alpha}\right)$$

**Unsuccessful search (key doesn't exist)**:

$$E[\text{probes}] = \frac{1}{2}\left(1 + \frac{1}{(1 - \alpha)^2}\right)$$

| Load Factor α | Successful Search (avg) | Unsuccessful Search (avg) |
| --- | --- | --- |
| 0.50 | 1.5 probes | 2.5 probes |
| 0.70 | 2.2 probes | 6.1 probes |
| 0.80 | 3.0 probes | 13.0 probes |
| 0.90 | 5.5 probes | 50.5 probes |
| 0.95 | 10.5 probes | 200.5 probes |

**For linear probing, performance degrades sharply beyond α = 0.7.** Unsuccessful searches (when the key doesn't exist) are particularly sensitive since they must probe until finding an empty slot. These numbers apply to linear probing specifically because of **clustering** — collisions pile up immediately adjacent, and the piled data triggers more collisions in a positive feedback loop.

However, **not all open addressing schemes are bound by these numbers.** Quadratic probing disperses probes at squared intervals, reducing cluster formation. Robin Hood Hashing reduces variance in probe distances, suppressing worst-case behavior. SwissTable uses SIMD to compare 16 slots at once, reducing probe cost itself. Thanks to these techniques, Rust `HashMap` allows α=0.875, and Go `map` allows 6.5 per bucket (effective α≈0.81). The load factor comparison table below shows these differences.

![Performance Change by Load Factor (α) in Linear Probing](/assets/img/post/cs/excalidraw-02-load-factor-en.png)

### Quadratic Probing — Dispersing Clusters

To reduce linear probing's clustering, probe at **quadratic intervals**:

$$h(k, i) = (h(k) + c_1 i + c_2 i^2) \mod m$$

Typically with $c_1 = 0, c_2 = 1$:

$$h(k, i) = (h(k) + i^2) \mod m$$

Probe sequence: +1, +4, +9, +16, ... Jumping increasingly farther mitigates primary clustering.

Drawback: **secondary clustering** — keys with the same initial hash value follow identical probe paths. Also, without proper selection of table size, $c_1$, and $c_2$, **not all slots may be visited.** It is safe when the table size is prime and the load factor is 0.5 or below.

### Robin Hood Hashing — Steal from the Rich, Give to the Poor

A technique proposed in Pedro Celis's 1986 PhD thesis, a variant of linear probing. Core idea:

> **During insertion, if I've traveled farther than the existing element at the current slot, I displace it and take its place.**

The distance from the "home position" (ideal position) is called **DIB (Distance from Initial Bucket)**.

```
Inserting "D" (home=2, current probe position=5, DIB=3)

[0]     [1]     [2]     [3]     [4]     [5]     [6]     [7]
         A       B       C       E       F
        DIB=0   DIB=0   DIB=1   DIB=3   DIB=1

"D"'s DIB=3. "F" at position 5 has DIB=1.
3 > 1, so "D" displaces "F" and takes position 5.
"F" is displaced and searches for the next empty slot.

Result:
[0]     [1]     [2]     [3]     [4]     [5]     [6]     [7]
         A       B       C       E       D       F
        DIB=0   DIB=0   DIB=1   DIB=3   DIB=3   DIB=2
```

**Effect**: All elements end up with similar DIB values. The maximum probe distance decreases, and the **variance** of probe distances drops dramatically. The average stays the same, but the worst case improves.

| Property | Linear Probing | Robin Hood Hashing |
| --- | --- | --- |
| Average probe distance | Same | Same |
| Maximum probe distance | Can be large | **Significantly reduced** |
| Variance | Large | **Small** |
| Insertion cost | Low | Slightly higher (swap) |

Rust's `HashMap` used Robin Hood Hashing for a long time (now switched to SwissTable-based `hashbrown`). This is evidence that the technique is effective in practice.

> **Let's pause and address this**
>
> **Q. How do you handle deletion in open addressing?**
>
> You can't simply empty the slot. During probing, encountering an empty slot means "not found." Instead, place a **tombstone** marker at the deleted position. During searches, tombstones are treated as "continue past here," and during insertions, as "you can insert here."
>
> As tombstones accumulate, search performance degrades, so periodic resizing (or reinsertion) is needed to clean them up.
>
> **Q. Chaining vs open addressing — which is faster in practice?**
>
> **In most benchmarks, linear probing is faster than chaining** — due to cache locality. However, this can reverse at high load factors. Modern high-performance hash tables (Google SwissTable, Facebook F14, Rust hashbrown) are **all based on open addressing**.

---

## Part 4: Load Factor and Resizing

### Load Factor

$$\alpha = \frac{n}{m}$$

- $n$: Number of stored elements
- $m$: Array (bucket) size
- $\alpha$: Load Factor

The load factor is the **density** of the hash table. α = 0 means completely empty, α = 1 means full (for open addressing). In chaining, α > 1 is possible, but performance suffers.

### Load Factor Thresholds by Language

| Language/Implementation | Max Load Factor | Collision Resolution | Resizing |
| --- | --- | --- | --- |
| Java `HashMap` | **0.75** | Chaining (→ tree conversion) | 2x |
| .NET `Dictionary` | **1.0** (when entries are full) | In-array chaining | ~2x in primes |
| Python `dict` | **0.67** | Open addressing | 4x (small) / 2x |
| Go `map` (~1.23) | **6.5** (per bucket) | Chaining (8-slot buckets) | 2x |
| Go `map` (1.24+) | Switched to Swiss Tables | Open addressing (Swiss Tables) | 2x |
| Rust `HashMap` | **0.875** | Robin Hood → SwissTable | 2x |

Java is unique in that when a single bucket accumulates **8 or more** elements, it converts the linked list to a **red-black tree**. This is a defensive mechanism that prevents O(n) degradation by capping it at O(log n). More precisely, this tree conversion only occurs **when the total table capacity is 64 or more**. When the table is small, **resizing (expanding the array)** is more effective than tree conversion — distributing collisions by increasing bucket count is cheaper than building a tree in a small table. The `MIN_TREEIFY_CAPACITY = 64` constant in the OpenJDK source defines this condition.

### The Cost of Resizing

Resizing consists of three steps:

1. Allocate a new array (typically 2x size)
2. **Rehash** all elements — hash values remain the same, but `hash % newSize` changes, so positions shift
3. Free the old array

Total **O(n)**. But applying **amortized analysis** as we learned in Part 2, the total resizing cost for n insertions is O(n), so the cost per insertion is **amortized O(1)**.

![Hash Table Resizing and Amortized Analysis](/assets/img/post/cs/excalidraw-03-resizing-en.png)

The lesson for game development is the same as Part 2: **if you know the element count in advance, set the initial capacity to prevent resizing entirely.** At 60fps with a 16.67ms frame budget, a hash table resizing spike can cause frame drops.

---

## Part 5: Cache Performance — Chaining vs Open Addressing

In Part 1, we examined the cache performance difference between arrays and linked lists. The exact same principle applies to the two hash table strategies.

### Memory Access Pattern of Chaining

```
Bucket array: [ptr0] [ptr1] [ptr2] [ptr3] [ptr4] ...  ← contiguous memory

Chain nodes:
0x1000: Node(Goblin) → next: 0x5040
0x5040: Node(Slime)  → next: NULL

Following pointers = non-sequential memory access → cache misses
```

- Bucket array access: O(1), cache hit (it's an array)
- Chain node access: pointer chasing → **high probability of cache misses**
- Extra memory per node: pointer (8 bytes) + heap allocation overhead

### Memory Access Pattern of Linear Probing

```
Slot array: [Goblin][Slime][Orc][ ][ ][Dragon][ ][ ] ← entirely contiguous memory

On collision, move to next slot → sequential memory access → cache hit
```

- All accesses occur within a single array
- Sequential probing is **movement within a cache line** — L1 hit
- Extra memory overhead: none (or just a tombstone bit)

### Google SwissTable's Approach

Google's **SwissTable** (2017), included in the Abseil library, is a milestone in modern hash table design. Core ideas:

1. **Metadata array (control bytes)**: A 1-byte control byte is stored in a separate array for each slot. The **most significant bit (MSB)** of this byte determines the slot's state
2. **SIMD probing**: Compare 16 control bytes **at once** using a single SSE2 instruction

Structure of a control byte:

```
Control byte interpretation:

MSB = 0 (0x00~0x7F): Slot is FULL
  → Lower 7 bits = upper 7 bits of the hash (called H2)
  → Example: 0x31 = full, H2=0x31

MSB = 1 (0x80~0xFF): Special state
  → 0xFF = EMPTY
  → 0xFE = DELETED (tombstone)

Control bytes example (group of 16):
[0x31][0xFF][0x55][0xFF][0x31][0x72][0xFF][0xFF]
[0xFF][0x1A][0xFF][0xFF][0xFF][0xFF][0xFE][0xFF]
 FULL  EMPTY FULL EMPTY FULL  FULL EMPTY EMPTY
                                    DEL  EMPTY
```

The lookup process for key "Orc":

```
1. Compute hash("Orc")
2. Select a group (16 slots) using the lower bits of the hash
3. Extract the upper 7 bits of the hash → H2 = 0x31
4. SIMD compares all 16 control bytes in the group against 0x31
   → H2 matches at index 0 and 4!
5. Perform actual key comparison only at matched slots (0, 4)
   → index 0: key mismatch, index 4: "Orc" confirmed!

Most cases: 1 SIMD operation + 1~2 key comparisons
```

**Why is this fast?** The key is the **dramatic reduction in comparison count**. Traditional linear probing must compare the full key at every slot. SwissTable filters 16 control bytes at once via SIMD, then performs actual key comparison only at slots where H2 matches (typically 0~2). Since 64 control bytes fit in a single cache line (64 bytes), metadata access is almost always resolved in L1 cache.

The influence of this design:
- C++ Abseil `absl::flat_hash_map`
- Rust `hashbrown` (SwissTable port → standard HashMap)
- Go 1.24+ `runtime.map` (Swiss Tables adopted, replacing the previous bucket chaining)

> **Let's pause and address this**
>
> **Q. What is SIMD?**
>
> SIMD (Single Instruction, Multiple Data) is a CPU feature that **processes multiple data elements simultaneously with a single instruction**. SSE2's `_mm_cmpeq_epi8` compares 16 bytes at once. SwissTable is a case of directly leveraging this hardware capability in data structure design. SIMD will be covered in depth in Phase 7 (advanced optimization).
>
> **Q. So which hash table should I use in game development?**
>
> - **C#/Unity**: `Dictionary<K,V>` is already cache-friendly with in-array chaining. Sufficient for most cases.
> - **C++/Unreal**: `TMap` (default), consider `absl::flat_hash_map` when high performance is needed.
> - **Custom engines**: Consider implementing Robin Hood Hashing or SwissTable directly. The difference becomes meaningful when lookups of tens of thousands of objects occur every frame.

---

## Part 6: Hash Table Applications — In Game Development

### 1. Spatial Hashing — Collision Detection Optimization

In 2D/3D games, naive collision detection among N objects requires **O(N²)** pair comparisons. Spatial hashing reduces this to **near O(N)**.

```
Divide space into a grid and hash objects into cells

┌──────┬──────┬──────┬──────┐
│      │  A   │      │      │
│      │      │      │      │
├──────┼──────┼──────┼──────┤
│      │ B  C │  D   │      │    B and C are in the same cell
│      │      │      │      │    → only check collision between these two
├──────┼──────┼──────┼──────┤
│      │      │      │  E   │
│      │      │      │      │
└──────┴──────┴──────┴──────┘

Hash function: h(x, y) = (x / cellSize, y / cellSize)
Hash table: {(1,0): [A], (1,1): [B,C], (2,1): [D], (3,2): [E]}
```

Only objects in the same cell need collision checking. Even including adjacent cells, only a constant number of cells (at most 9, or 27 in 3D) need to be examined.

This technique is widely used in particle systems, crowd simulation, and the broad phase of physics engines.

### 2. String Interning

Strings appear everywhere in games: event names, tags, resource paths. Comparing strings each time costs O(L).

**String interning**: A technique that **maintains only a single instance** of strings with the same content. Strings are stored in a hash table, and if the same content exists, the existing instance is returned.

```csharp
// Before interning: string comparison = O(L), proportional to length
if (eventName == "OnPlayerDeath") { ... }

// After interning: reference comparison = O(1)
// string.Intern() stores in the CLR interning pool
string interned = string.Intern("OnPlayerDeath");
if (ReferenceEquals(eventName, interned)) { ... }
```

Unreal Engine's `FName` works on exactly this principle. Strings are stored in a hash table, and subsequent comparisons use integer indices. String comparison O(L) → integer comparison O(1).

### 3. Memoization — Caching Computation Results

Cache the results of expensive computations in a hash table:

```csharp
// Cache pathfinding results
private Dictionary<(Vector2Int from, Vector2Int to), List<Vector2Int>> pathCache;

public List<Vector2Int> FindPath(Vector2Int from, Vector2Int to) {
    if (pathCache.TryGetValue((from, to), out var cached))
        return cached;  // O(1) cache hit

    var path = AStar(from, to);  // expensive computation
    pathCache[(from, to)] = path;
    return path;
}
```

### 4. Duplicate Detection

Visited nodes, processed events, loaded resources — check "has this been done already?" in O(1):

```csharp
HashSet<int> visitedNodes = new();  // internally a hash table

void BFS(int start) {
    var queue = new Queue<int>();
    queue.Enqueue(start);
    visitedNodes.Add(start);

    while (queue.Count > 0) {
        int current = queue.Dequeue();
        foreach (int neighbor in GetNeighbors(current)) {
            if (visitedNodes.Add(neighbor)) {  // O(1) duplicate check + insertion
                queue.Enqueue(neighbor);
            }
        }
    }
}
```

`HashSet` is a hash table with keys only. In Part 2's BFS, we checked visit status with `distance[nx, ny] == -1`, but for non-grid graphs, `HashSet` is needed.

---

## Part 7: Limitations and Security of Hash Tables

### HashDoS — Hash Collision Attacks

In 2011, Alexander Klink and Julian Waelde published the **HashDoS** attack: by deliberately sending a large number of keys with the same hash value, a hash table degrades to O(n²).

Since web servers store HTTP parameters in hash tables, sending tens of thousands of colliding keys can freeze the server. This attack affected web frameworks in virtually every language — PHP, Java, Python, Ruby, .NET, and more.

**Countermeasures**:
- **Randomized seed hashing (Keyed Hash)**: Mix a secret seed per process to make the hash function unpredictable. Python has applied this since 3.3, .NET Core by default
- **SipHash**: A hash function designed by Jean-Philippe Aumasson for "short input safety." Used by default in Rust, Python, and Ruby
- **Tree conversion**: Java HashMap's conversion to red-black tree when a chain exceeds 8 elements

This is a valid threat for game servers too. If client-sent data is stored in hash tables (inventory, chat filters, etc.), HashDoS should be considered.

### Hash Tables vs Sorted Structures

| Property | Hash Table | Balanced Binary Tree (Part 4 preview) |
| --- | --- | --- |
| Average lookup | **O(1)** | O(log n) |
| Worst-case lookup | O(n) | **O(log n)** |
| Order guarantee | None | **Yes** |
| Range queries | Not possible | **Possible** |
| Memory overhead | Medium (empty slots) | High (pointers) |
| Min/Max | O(n) | **O(log n)** |

Hash tables are optimal for **point queries** — "what is the value for this key?" They are unsuitable for **range queries** like "find all keys between 100 and 200" or requirements like "iterate in key order." For such cases, the **tree structures** covered in Part 4 are needed.

---

## Conclusion: O(1) Isn't Free

Key takeaways from this article:

1. **Hash table O(1) depends on hash function quality.** A poor hash function concentrates collisions and turns O(1) into O(n). This is why primes are used in the division method and the golden ratio in the multiplication method.

2. **Collisions are unavoidable** — the pigeonhole principle and birthday paradox guarantee this mathematically. **How you resolve collisions** defines the character of the hash table. Chaining is simple but cache-unfriendly, while open addressing (especially linear probing) is cache-friendly but vulnerable to clustering.

3. **Load factor (α) is the key performance regulator.** For linear probing, beyond α = 0.7 collisions surge, and beyond 0.9 it becomes practically unusable. However, the tolerable load factor varies by collision resolution strategy — Quadratic probing, Robin Hood Hashing, SwissTable, etc. can operate stably at higher load factors thanks to cluster mitigation or SIMD parallel comparison. Resizing is O(n) but amortized O(1) — yet in games, preventing it entirely through initial capacity settings is best.

4. **Cache performance matters as much as theoretical complexity.** The lesson from Part 1 repeats here. Google SwissTable's use of SIMD to compare 16 slots at once is not an algorithmic innovation but a **design innovation aligned with hardware characteristics**.

5. **Hash tables are not a silver bullet.** When you need ordering, range queries, or worst-case guarantees, tree structures are the answer.

Knuth summarized hashing in TAOCP Vol. 3:

> "Hashing is a classical example of a time-space tradeoff."

By accepting the **wasted space** of empty slots, we gain **O(1) time**. Understanding this tradeoff and finding the balance point through load factor and hash function quality is how to use hash tables correctly.

In the next installment, we'll cover **Trees** — structures that maintain order while guaranteeing O(log n), from BST to Red-Black Tree to B-Tree.

---

## References

**Key Papers and Technical Documents**
- Knuth, D., *The Art of Computer Programming Vol. 3: Sorting and Searching*, Addison-Wesley — Classic analysis of hashing (Chapter 6.4), proof of linear probing average probe length
- Celis, P., "Robin Hood Hashing", PhD Thesis, University of Waterloo (1986) — Original source of Robin Hood Hashing
- Aumasson, J.P. & Bernstein, D.J., "SipHash: a fast short-input PRF", INDOCRYPT (2012) — Hash function for HashDoS defense
- Klink, A. & Waelde, J., "Efficient Denial of Service Attacks on Web Application Platforms", 28C3 (2011) — Original source of the HashDoS attack
- Abseil Team, "Swiss Tables Design Notes" — [abseil.io](https://abseil.io/about/design/swisstables) — SIMD-based SwissTable design

**Talks and Presentations**
- Kulukundis, M., "Designing a Fast, Efficient, Cache-friendly Hash Table, Step by Step", CppCon 2017 — SwissTable design process
- Chandler Carruth, "High Performance Code 201: Hybrid Data Structures", CppCon 2016 — Cache-friendly hash table design

**Textbooks**
- Cormen, T.H. et al., *Introduction to Algorithms (CLRS)*, MIT Press — Hash Tables Chapter 11, Universal Hashing, Perfect Hashing
- Bryant, R. & O'Hallaron, D., *Computer Systems: A Programmer's Perspective (CS:APP)*, Pearson — How memory hierarchy and cache affect data structure performance
- Bloch, J., *Effective Java*, 3rd Edition, Addison-Wesley — Item 11: hashCode implementation guide
- Sedgewick, R. & Wayne, K., *Algorithms*, 4th Edition, Addison-Wesley — Linear Probing, Separate Chaining implementation and analysis

**Implementation References**
- .NET `Dictionary<TKey, TValue>` — [dotnet/runtime source](https://github.com/dotnet/runtime): In-array chaining, prime-based resizing
- Java `HashMap` — [OpenJDK source](https://github.com/openjdk/jdk): Chaining → tree conversion, perturbation
- Rust `hashbrown` — [crates.io](https://crates.io/crates/hashbrown): SwissTable port, foundation of Rust's standard HashMap
- Google `absl::flat_hash_map` — Abseil library: SwissTable C++ reference implementation
- Facebook `folly::F14` — [github.com/facebook/folly](https://github.com/facebook/folly): SIMD-based open addressing
