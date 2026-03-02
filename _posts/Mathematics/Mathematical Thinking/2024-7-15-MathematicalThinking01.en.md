---
title: Mathematical Thinking - Sets, Propositions, and Axioms
date: 2024-7-15 17:42:00 +/-TTTT
categories: [Mathematics, Mathematical Thinking]
tags: [mathematics, set theory, proposition, axiom, cantor]
lang: en
difficulty: intermediate
toc: true
toc_sticky: true
math: true
use_math: true
mermaid: true
---

[![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fepheria.github.io&count_bg=%2379C83D&title_bg=%23555555&icon=&icon_color=%23E7E7E7&title=views&edge_flat=false)](https://hits.seeyoufarm.com)

---

> **Purpose of this article**
> Reading graduate-level papers requires understanding mathematical formulas and proofs. This article serves as a starting point by organizing the core concepts of **sets, propositions, and axioms**.
{: .prompt-info}

> Understanding, not just doing.
{: .prompt-tip}

<br>

## Introduction - Determining Truth in Mathematics

The primary means of determining truth in mathematics is **"proof"**.

Mathematical claims always deal only with **true** and **false**. That is, for any claim we determine **Yes** or **No**, which is equivalent to **determining whether something belongs to a particular set.**

<br>

## I. Logical Connectives

These are the basic connectives used to construct and combine mathematical propositions.

### 1. and (Conjunction)

$$p \land q$$

True only when both propositions $p$ and $q$ are **both true**.

| $p$ | $q$ | $p \land q$ |
|-----|-----|-------------|
| T   | T   | T           |
| T   | F   | F           |
| F   | T   | F           |
| F   | F   | F           |

### 2. or (Disjunction)

$$p \lor q$$

True when **at least one** of the two propositions is true. (In mathematics, "or" is inclusive or)

| $p$ | $q$ | $p \lor q$ |
|-----|-----|------------|
| T   | T   | T          |
| T   | F   | T          |
| F   | T   | T          |
| F   | F   | F          |

### 3. not (Negation)

$$\neg p$$

**Reverses** the truth value of proposition $p$. True becomes false, false becomes true.

### 4. implies (Implication)

$$p \Rightarrow q$$

"If $p$ then $q$." False only when $p$ is true and $q$ is false.

| $p$ | $q$ | $p \Rightarrow q$ |
|-----|-----|--------------------|
| T   | T   | T                  |
| T   | F   | F                  |
| F   | T   | T                  |
| F   | F   | T                  |

> The reason $p \Rightarrow q$ is always true when $p$ is false: "Anything can be derived from a false premise" (vacuous truth)
{: .prompt-warning}

### 5. for all (Universal Quantifier)

$$\forall x \in S, \; P(x)$$

The proposition $P(x)$ is true for **all** elements $x$ of set $S$.

### 6. there exists (Existential Quantifier)

$$\exists x \in S, \; P(x)$$

There exists **at least one** element $x$ in set $S$ that satisfies proposition $P(x)$.

<br>

---

## II. Set

> **Terminology**
> * Set = Collection =? Family (family of sets)
{: .prompt-info}

### Elements and Sets

**Example)** A dog is not a cat.

$$\iff \text{A dog does not belong to the collection of cats.}$$

$$\iff \text{dog} \notin \{\text{cat1}, \text{cat2}, \text{cat3}, \cdots\}$$

Here $\notin$ means "does not belong to" and is the negation of $\in$.

**Abstracting** this:

- Dog $\Leftrightarrow x$
- Collection of cats $\Leftrightarrow S$

$$\implies x \notin S$$

- $x$ is called an **element**, $S$ is called a **set**.
- **What is an element?** Something that belongs to a set.

### What is a Set?

> A collection of elements that satisfy some criterion

is what we learned in school. But is that really the case?

### Russell's Paradox

**A barber says:** "I will shave only those who do not shave themselves."

- Establishing the criterion → Set $S$ = {those whom the barber shaves}
- Then, barber $x$ must be an element of $S$ and simultaneously not be an element of $S$. **Contradiction!**

This is called the **Barber's Paradox**.

> **The problem:** Since we regarded a set simply as "a collection of elements," something more is needed in the process of defining sets. This "something" is what we call an **axiom**.
{: .prompt-danger}

<br>

---

## III. Number Systems and the Size of Sets

### Number System Hierarchy

$$\mathbb{N} \subset \mathbb{Z} \subset \mathbb{Q} \subset \mathbb{R}$$

| Symbol | Name | Examples |
|--------|------|----------|
| $\mathbb{N}$ | Natural numbers | $1, 2, 3, 4, \cdots$ |
| $\mathbb{Z}$ | Integers | $\cdots, -2, -1, 0, 1, 2, \cdots$ |
| $\mathbb{Q}$ | Rational numbers | $\frac{2}{3}, -\frac{5}{7}, \cdots$ |
| $\mathbb{R}$ | Real numbers | $\sqrt{2}, \pi, 3.14\cdots$ |

### Counter-Intuitive Questions

1. Is the set of integers larger than the set of natural numbers?
2. Is the set of rational numbers larger than the set of integers?

> The answer to all these questions is **false**!
{: .prompt-warning}

<br>

### 1) Natural Numbers ↔ Integers: One-to-One Correspondence

Let's split the set of natural numbers into the **set of even numbers** and the **set of odd numbers**.

**For even numbers:**

$$0\;(=2 \times 0) \to 0, \quad 2\;(=2 \times 1) \to 1, \quad 4\;(=2 \times 2) \to 2$$

In general:

$$2n \to n$$

**For odd numbers:**

$$1\;(=2 \times 0 + 1) \to -1, \quad 3\;(=2 \times 1 + 1) \to -2, \quad 5\;(=2 \times 2 + 1) \to -3$$

In general:

$$2n + 1 \to -(n+1)$$

That is, natural numbers and integers correspond to each other one by one. Therefore, **the number of elements in the set of integers equals the number of elements in the set of natural numbers**.

> In particular, one can observe that the set of even numbers, the set of odd numbers, and the set of natural numbers are all in one-to-one correspondence. (Exercise)
{: .prompt-tip}

<br>

### 2) Integers ↔ Rational Numbers: One-to-One Correspondence

Integers consist of positive integers, 0, and negative integers, and rational numbers likewise consist of positive rationals, 0, and negative rationals. We can map the zeros to each other, and we need to find a **one-to-one correspondence** between positive integers (i.e., natural numbers) and positive rational numbers. (The negative case follows by changing signs)

Since every positive rational number can be written as a fraction $\frac{m}{n}$, let's arrange those with the same denominator as follows:

$$\frac{1}{1}, \frac{2}{1}, \frac{3}{1}, \frac{4}{1}, \frac{5}{1}, \frac{6}{1}, \frac{7}{1}, \frac{8}{1}, \cdots$$

$$\frac{1}{2}, \frac{2}{2}, \frac{3}{2}, \frac{4}{2}, \frac{5}{2}, \frac{6}{2}, \frac{7}{2}, \frac{8}{2}, \cdots$$

$$\frac{1}{3}, \frac{2}{3}, \frac{3}{3}, \frac{4}{3}, \frac{5}{3}, \frac{6}{3}, \frac{7}{3}, \frac{8}{3}, \cdots$$

$$\vdots$$

To establish a one-to-one correspondence with positive integers (natural numbers) is the same as finding a way to **count** all positive rational numbers one by one sequentially.

One method is to count the listed positive rational numbers **diagonally:**

$$\frac{1}{1} \to \frac{2}{1} \to \frac{1}{2} \to \frac{1}{3} \to \frac{2}{2} \to \frac{3}{1} \to \frac{4}{1} \to \frac{3}{2} \to \frac{2}{3} \to \frac{1}{4} \to \cdots$$

> This counting method is known as **diagonal enumeration**. Since we can count positive rational numbers sequentially, a one-to-one correspondence with positive integers holds.
{: .prompt-tip}

Therefore, by the above argument, **a one-to-one correspondence between integers and rational numbers holds**.

<br>

### 3) Rational Numbers ↔ Real Numbers: Does a One-to-One Correspondence Hold?

> The answer is again **false**!
{: .prompt-danger}

We aim to show the conclusion is true by **negating it and deriving a contradiction** (this form of argument is called **proof by contradiction**).

Suppose a one-to-one correspondence between rational numbers and real numbers holds. From what we've already confirmed in 1) and 2), we know that **a one-to-one correspondence between natural numbers and rational numbers holds**. Therefore, if a one-to-one correspondence between rational and real numbers holds, then **a one-to-one correspondence between natural numbers and real numbers must hold**.

This means we should be able to list all real numbers one by one in correspondence with natural numbers. Then, for **any subset of real numbers**, we should also be able to count them sequentially. We will choose a specific subset of real numbers and verify that this is **impossible**.

#### Cantor's Diagonal Argument

Consider **the collection of all real numbers between 0 and 1**.

Real numbers between 0 and 1 can always be written in the following form:

$$0.a_1 a_2 a_3 a_4 \cdots \quad \text{(each } a_n \text{ is a digit from 0 to 9)}$$

$$\text{e.g., } 0.1, \quad 0.22, \quad 0.1234567890\cdots$$

Since we should be able to count all real numbers between 0 and 1 sequentially, let's number them:

$$x_1, x_2, x_3, x_4, \cdots$$

Writing them out:

$$x_1 = 0.\color{red}{a_1^1} a_2^1 a_3^1 a_4^1 a_5^1 \cdots$$

$$x_2 = 0.a_1^2 \color{red}{a_2^2} a_3^2 a_4^2 a_5^2 \cdots$$

$$x_3 = 0.a_1^3 a_2^3 \color{red}{a_3^3} a_4^3 a_5^3 \cdots$$

$$x_4 = 0.a_1^4 a_2^4 a_3^4 \color{red}{a_4^4} a_5^4 \cdots$$

$$x_5 = 0.a_1^5 a_2^5 a_3^5 a_4^5 \color{red}{a_5^5} \cdots$$

$$\vdots$$

Since all real numbers between 0 and 1 can be counted sequentially:

$$x_* = 0.a_1^* a_2^* a_3^* a_4^* a_5^* \cdots$$

every real number must be expressible in this form.

At this point, **consider the following number:**

$$X = 0.b_1 b_2 b_3 b_4 \cdots$$

where each $n$-th digit $b_n$ is defined as:

- If $a_n^n = 3$: $b_n = 5$
- If $a_n^n \neq 3$: $b_n = 3$

Then each digit $b_n$ of $X$ differs from $a_n^n$, so $X$ must differ from every $x_n$.

This contradicts **"every real number between 0 and 1 must be of the form $x_*$"**, and a **contradiction arises**.

Since this contradiction arose from **the assumption that a one-to-one correspondence between natural numbers and real numbers holds**, the desired conclusion follows.

> The above argument is called the **diagonal method** by **Cantor (1845-1918, founder of set theory)**.
{: .prompt-info}

<br>

### Points to Consider

The set of natural numbers is contained in the set of integers. There exist integers that are not natural numbers, and the set of integers is contained in the set of rational numbers. Again, there exist rationals that are not integers. **Yet, a one-to-one correspondence is possible among all three sets.**

Why does this (counter-intuitive) situation occur? This is possible because the set of natural numbers, the set of integers, and the set of rational numbers are all **infinite sets**.

However, **not all infinite sets can be put into one-to-one correspondence.** Among infinite sets, there are (somewhat surprisingly) genuine differences. Like the case of natural numbers and real numbers. At the very least, the set of real numbers is **'larger'** than the set of natural numbers — too large to be counted one by one!

> In set theory, the size of sets including infinite sets is called a cardinal number, or **Cardinal Number**.
{: .prompt-info}

<br>

### The Continuum Hypothesis

> **Question:** Does there exist an infinite set that is 'larger' than the set of natural numbers but 'smaller' than the set of real numbers?
{: .prompt-warning}

This question was first posed by Cantor and corresponds to **Problem 1** among the 23 important problems presented by David Hilbert at the 1900 International Congress of Mathematicians. This is called the **Continuum Hypothesis**.

- **1940**: Kurt Gödel proved it **cannot be disproved**
- **1963**: Paul Cohen proved it **cannot be proved**

The conclusion is that **there is no answer**. It is consistent to assume it true, and equally consistent to assume it false.

> A detailed discussion requires understanding the **ZFC axiom system** of set theory.
{: .prompt-info}

<br>

---

## IV. Axiom

Ultimately, what we accept as true falls in the domain of **'choice'**, and my choices need not coincide with another's. Even **within the realm of mathematics**.

### Axioms of Euclidean Geometry

Were there propositions we accepted as necessarily true during our school years that were actually neither true nor false?

- **(Pythagorean Theorem)** The square of the hypotenuse of a right triangle equals the sum of the squares of the other two sides.

$$b^2 + c^2 = a^2$$

- **(Triangle Angle Sum)** The sum of interior angles of every triangle is $180°$.

$$\alpha + \beta + \gamma = 180°$$

- Rectangles exist.
- **(Equidistance Postulate)** The distance between two parallel lines is constant everywhere.
- **(Parallel Postulate)** If two lines meet a third line such that the sum of the co-interior angles on one side is less than two right angles, then extending the two lines indefinitely, they meet on that side.

> In fact, the above five statements are all mathematically **equivalent**.
{: .prompt-warning}

**Euclidean geometry** (what we learned in middle school), written in the 3rd century BCE, was built upon five postulates (axioms), the fifth of which is the **Parallel Postulate**.

In the 19th century, it was discovered that **negating** the 5th postulate creates no contradiction with the other axioms. Much like the Continuum Hypothesis.

> **Non-Euclidean geometry**: Geometry that negates the 5th postulate. In modern mathematics, it is generally called **Riemannian geometry**. Bernhard Riemann, after whom it is named, was a student of Gauss.
{: .prompt-info}

> Non-Euclidean geometry is not merely central to pure mathematics — it naturally appears as a mathematical model in Bayesian statistics (central to modern statistics), coding and information theory, the physical spacetime we live in, and more.
{: .prompt-tip}

<br>

---

## V. Conclusion

Discussing mathematical truth and falsehood requires the **choice of axioms**. Especially when dealing with mathematical objects like infinite sets where intuition and reality can diverge, the appropriate **choice of axioms is indispensable**.

However, the appropriate choice of axioms is a domain of **choice and belief dependent on individual (and human) rationality**. Put another way, one must decide which **'lens'** to use when viewing a given subject before one can discuss truth and falsehood.

<br>

---

# Part 2. Extension to Graduate Level

> From here, these are concepts essential for reading graduate-level papers. We build **rigorous definitions and proof techniques** on top of Part 1's intuitive understanding.
{: .prompt-info}

<br>

## VI. Proof Techniques

Proofs are what you encounter most frequently in graduate papers. Knowing proof patterns makes papers **readable**.

### 1. Direct Proof

A method of starting from assumption $P$ and arriving at conclusion $Q$ through logical steps.

**Example:** If $n$ is even, then $n^2$ is also even.

> **Proof.** Since $n$ is even, $n = 2k$ ($k$ is an integer). Then $n^2 = (2k)^2 = 4k^2 = 2(2k^2)$. Since $2k^2$ is an integer, $n^2$ is even. $\blacksquare$

### 2. Proof by Contrapositive

When it is difficult to show $P \Rightarrow Q$ directly, we prove the logically equivalent $\neg Q \Rightarrow \neg P$.

$$P \Rightarrow Q \;\equiv\; \neg Q \Rightarrow \neg P$$

**Example:** If $n^2$ is odd, then $n$ is also odd.

> **Proof.** Contrapositive: "If $n$ is even, then $n^2$ is also even." This was already proved above. $\blacksquare$

> When the phrase "we prove the contrapositive" appears in a paper, this is the pattern.
{: .prompt-tip}

### 3. Proof by Contradiction

A method of negating the conclusion and deriving a contradiction. Cantor's diagonal argument from Part 1 was a representative example.

**Structure:**
1. What we want to prove: $P$
2. Assume $\neg P$
3. Through logical reasoning, arrive at a contradiction ($Q \land \neg Q$)
4. Therefore $\neg P$ is false, so $P$ is true

**Classic example:** $\sqrt{2}$ is irrational.

> **Proof.** Suppose $\sqrt{2}$ is rational. Then $\sqrt{2} = \frac{p}{q}$ (where $p, q$ are coprime integers). Squaring both sides gives $2 = \frac{p^2}{q^2}$, i.e., $p^2 = 2q^2$. So $p^2$ is even, hence $p$ is also even. Setting $p = 2m$ gives $4m^2 = 2q^2$, i.e., $q^2 = 2m^2$. So $q$ is also even. But if both $p$ and $q$ are even, this **contradicts** the assumption that they are coprime. $\blacksquare$

### 4. Mathematical Induction

A technique for proving a proposition $P(n)$ about natural numbers for all $n$.

**Structure:**
1. **Base case:** Show that $P(1)$ is true
2. **Inductive step:** Assume $P(k)$ is true ($\leftarrow$ induction hypothesis), and show $P(k+1)$ is true

**Example:** $1 + 2 + 3 + \cdots + n = \frac{n(n+1)}{2}$

> **Proof.**
> - **Base:** When $n = 1$, LHS $= 1$, RHS $= \frac{1 \cdot 2}{2} = 1$. Holds. $\checkmark$
> - **Inductive step:** Assume $1 + 2 + \cdots + k = \frac{k(k+1)}{2}$ holds. Adding $(k+1)$ to both sides:
>
> $$1 + 2 + \cdots + k + (k+1) = \frac{k(k+1)}{2} + (k+1) = \frac{k(k+1) + 2(k+1)}{2} = \frac{(k+1)(k+2)}{2}$$
>
> This matches $P(k+1)$. $\blacksquare$

### 5. Strong Induction

In the inductive step, we assume not just $P(k)$ but **all of** $P(1), P(2), \cdots, P(k)$ and show $P(k+1)$. Frequently appears in proofs with recursive structures.

### 6. Constructive vs Non-Constructive Proofs

| Constructive | Non-constructive |
|---|---|
| When claiming existence, **actually construct** it | Show that non-existence leads to contradiction (without constructing) |
| Directly translatable to algorithms | Existence is known but the method to find it may not be |

> In game development, **constructive proof thinking** is more useful. The habit of thinking "here's how to build it" rather than "this exists."
{: .prompt-tip}

<br>

---

## VII. Set Operations

### Basic Operations

For sets $A$ and $B$:

| Operation | Notation | Definition |
|-----------|----------|------------|
| Union | $A \cup B$ | $\{x \mid x \in A \text{ or } x \in B\}$ |
| Intersection | $A \cap B$ | $\{x \mid x \in A \text{ and } x \in B\}$ |
| Difference | $A \setminus B$ | $\{x \mid x \in A \text{ and } x \notin B\}$ |
| Complement | $A^c$ | $\{x \in U \mid x \notin A\}$ (relative to universal set $U$) |
| Symmetric Difference | $A \triangle B$ | $(A \setminus B) \cup (B \setminus A)$ |

### De Morgan's Laws

$$\neg(P \land Q) \equiv (\neg P) \lor (\neg Q)$$

$$\neg(P \lor Q) \equiv (\neg P) \land (\neg Q)$$

Expressed in terms of sets:

$$(A \cap B)^c = A^c \cup B^c$$

$$(A \cup B)^c = A^c \cap B^c$$

> These always appear when **negating quantifiers** in papers:
> - $\neg(\forall x, P(x)) \equiv \exists x, \neg P(x)$ — The negation of "all are P" is "there exists one that is not P"
> - $\neg(\exists x, P(x)) \equiv \forall x, \neg P(x)$ — The negation of "P exists" is "all are not P"
{: .prompt-warning}

### Power Set

The set of **all subsets** of a set $A$.

$$\mathcal{P}(A) = \{S \mid S \subseteq A\}$$

**Example:** When $A = \{1, 2, 3\}$:

$$\mathcal{P}(A) = \{\emptyset, \{1\}, \{2\}, \{3\}, \{1,2\}, \{1,3\}, \{2,3\}, \{1,2,3\}\}$$

The size of the power set of a set with $n$ elements is $2^n$.

> **Cantor's Theorem:** For any set $A$, $|A| < |\mathcal{P}(A)|$. That is, any set is smaller than its power set. This holds even for infinite sets, and is the core principle behind "there are infinities of different sizes."
{: .prompt-info}

### Cartesian Product

$$A \times B = \{(a, b) \mid a \in A, \; b \in B\}$$

**Example:** If $A = \{1, 2\}$, $B = \{x, y\}$, then $A \times B = \{(1,x), (1,y), (2,x), (2,y)\}$

This is the mathematical foundation of coordinate systems. $\mathbb{R} \times \mathbb{R} = \mathbb{R}^2$ is precisely the 2-dimensional plane.

<br>

---

## VIII. Relations & Functions

### Relation

A **relation** $R$ from set $A$ to $B$ is a subset of the Cartesian product $A \times B$.

$$R \subseteq A \times B$$

If $a$ and $b$ are in relation $R$, we write $aRb$ or $(a, b) \in R$.

### Equivalence Relation

A relation $\sim$ on set $A$ is called an **equivalence relation** if it satisfies all three conditions:

1. **Reflexivity:** $a \sim a$
2. **Symmetry:** $a \sim b \Rightarrow b \sim a$
3. **Transitivity:** $a \sim b \land b \sim c \Rightarrow a \sim c$

**Example:** The "same remainder" relation on integers. $a \equiv b \pmod{n}$

$$7 \equiv 2 \pmod{5} \quad \text{(both have remainder 2 when divided by 5)}$$

> An equivalence relation partitions a set into non-overlapping groups. These are called **equivalence classes**, and the result is a **partition**. A core concept that appears everywhere in graduate mathematics.
{: .prompt-warning}

### Partial Order

A relation $\leq$ is called a **partial order** if it satisfies:

1. **Reflexivity:** $a \leq a$
2. **Antisymmetry:** $a \leq b \land b \leq a \Rightarrow a = b$
3. **Transitivity:** $a \leq b \land b \leq c \Rightarrow a \leq c$

If every pair of elements is comparable, it is a **total order**; otherwise, it is a **partial order**.

**Example:** The subset relation $\subseteq$ on sets is a partial order. $\{1\}$ and $\{2\}$ are incomparable.

### Rigorous Definition of Functions

A function $f: A \to B$ is a relation $f \subseteq A \times B$ such that **for each $a \in A$, there exists exactly one** $(a, b) \in f$.

| Type | Definition | Intuition |
|------|------------|-----------|
| **Injection** | $f(a_1) = f(a_2) \Rightarrow a_1 = a_2$ | Different inputs → Different outputs |
| **Surjection** | $\forall b \in B, \exists a \in A: f(a) = b$ | Every output is reachable |
| **Bijection** | Injection + Surjection | Perfect one-to-one correspondence |

### Cantor-Bernstein Theorem

$$|A| \leq |B| \text{ and } |B| \leq |A| \text{ implies } |A| = |B|$$

That is, if an injection from $A$ to $B$ and an injection from $B$ to $A$ both exist, then a bijection between $A$ and $B$ exists. A powerful tool: to show two sets have the same size, **it suffices to show injections in both directions**.

<br>

---

## IX. Preview of Key Concepts for Graduate Papers

> This section identifies "why it's needed" and "where you'll encounter it" for each concept. Rigorous definitions are covered in dedicated posts for each field.
{: .prompt-info}

### Topology - Open and Closed Sets

**Core idea:** A way to define "closeness." We can discuss "continuity" and "convergence" even without a metric (distance).

A **topology** $\tau$ on a set $X$ is a collection of subsets of $X$ such that:

1. $\emptyset, X \in \tau$
2. Any union of elements of $\tau$ belongs to $\tau$
3. Any finite intersection of elements of $\tau$ belongs to $\tau$

Elements of $\tau$ are called **open sets**.

> **Where you'll encounter this:** Manifold theory, differential geometry, data space analysis in ML. In particular, the mathematical foundation of mesh in graphics is topology.
{: .prompt-tip}

### Sigma-Algebra ($\sigma$-algebra) - Foundation of Measure Theory

The rigorous foundation of probability theory and integration theory. A $\sigma$-algebra $\mathcal{F}$ on a set $X$:

1. $X \in \mathcal{F}$
2. $A \in \mathcal{F} \Rightarrow A^c \in \mathcal{F}$ (closed under complements)
3. $A_1, A_2, \cdots \in \mathcal{F} \Rightarrow \bigcup_{i=1}^{\infty} A_i \in \mathcal{F}$ (closed under countable unions)

In a probability space $(\Omega, \mathcal{F}, P)$, $\mathcal{F}$ is precisely this. It defines "the collection of events for which we can ask about probability."

> **Where you'll encounter this:** Probability theory, statistics, when ML papers rigorously handle expectations and integrals. When the term "measurable function" appears in a paper, this is the concept.
{: .prompt-tip}

### Metric Space

A pair $(X, d)$ of a set $X$ and a distance function $d: X \times X \to \mathbb{R}$ such that:

1. $d(x, y) \geq 0$, and $d(x, y) = 0 \iff x = y$
2. $d(x, y) = d(y, x)$ (symmetry)
3. $d(x, z) \leq d(x, y) + d(y, z)$ (triangle inequality)

> **Where you'll encounter this:** Optimization theory, convergence proofs, algorithm analysis. In games, for an A* search heuristic to be admissible, it must satisfy the triangle inequality.
{: .prompt-tip}

### Norm & Inner Product

A **norm** $\|\cdot\|$ on a vector space $V$ abstracts "length," and an **inner product** $\langle \cdot, \cdot \rangle$ abstracts "angle."

$$\|v\| = \sqrt{\langle v, v \rangle}$$

$$\cos\theta = \frac{\langle u, v \rangle}{\|u\| \cdot \|v\|}$$

> **Where you'll encounter this:** `dot(normal, lightDir)` in shaders is exactly the inner product. It appears everywhere in ML: cosine similarity, graph Laplacians, and more.
{: .prompt-tip}

### Convergence & Limits - Epsilon-Delta

The rigorous definition of $\lim_{x \to a} f(x) = L$ for a function $f$:

$$\forall \epsilon > 0, \; \exists \delta > 0 : \; 0 < |x - a| < \delta \Rightarrow |f(x) - L| < \epsilon$$

**How to read it:** "No matter how small an error $\epsilon$ we choose, we can find a sufficiently small range $\delta$ around $a$."

> Once you understand this definition structure, the "$\forall \epsilon, \exists \delta$" pattern reads naturally every time it appears in papers.
{: .prompt-warning}

<br>

---

# Part 3. Mathematical Thinking in Practice for Game Developers

> Set theory, propositional logic, and proof techniques are not merely theoretical. They form a thinking framework unconsciously used throughout the **design, debugging, and optimization** process of game development. This section makes those connections explicit.
{: .prompt-info}

<br>

## X. Set-Theoretic Thinking → Game System Design

### 1. Bitmask = Implementation of Power Set

In games, component combinations, layer masks, and buff/debuff systems are all implementations of the **power set** using bits.

```csharp
// Unity's LayerMask is a 32-bit integer = 2^32 possible subsets
[Flags]
enum BuffType
{
    None     = 0,       // Empty set
    Speed    = 1 << 0,  // {Speed}
    Attack   = 1 << 1,  // {Attack}
    Defense  = 1 << 2,  // {Defense}
    Shield   = 1 << 3   // {Shield}
}

// Union: Add buffs
currentBuffs |= BuffType.Speed | BuffType.Attack;

// Intersection: Check for specific buff
bool hasSpeed = (currentBuffs & BuffType.Speed) != 0;

// Difference: Remove buff
currentBuffs &= ~BuffType.Defense;
```

**Mathematical correspondence:**

| Set Operation | Bit Operation | Use |
|----------|----------|------|
| $A \cup B$ | `a \| b` | Add states/buffs |
| $A \cap B$ | `a & b` | Check conditions |
| $A \setminus B$ | `a & ~b` | Remove states/buffs |
| $A^c$ | `~a` | Invert |
| $\mathcal{P}(A)$ | All bit combinations | Search entire state space |

> With $n$ buffs, there are $2^n$ possible combinations. With 20 buffs, that exceeds one million. This is the **mathematical reason** game balancing is difficult.
{: .prompt-warning}

### 2. ECS (Entity Component System) = Set Intersection Query

The core of Unity DOTS / ECS architecture is **set operations**.

```
// "Entities with both Position and Velocity" = intersection
query = EntityQuery.Where(has: Position ∩ Velocity)

// "Entities with Position but not Static" = difference
query = EntityQuery.Where(has: Position, exclude: Static)
// Mathematically: {e | e ∈ Position} \ {e | e ∈ Static}
```

### 3. Collision Layer Matrix = Matrix Representation of Relations

Unity's Physics Layer collision matrix defines **relations between sets**.

$$R \subseteq \text{Layers} \times \text{Layers}$$

"Player layer and Enemy layer collide" = $(Player, Enemy) \in R$

The fact that this relation is **symmetric** means $(A, B) \in R \Rightarrow (B, A) \in R$. This is why the physics engine only needs to check collisions in one direction.

<br>

---

## XI. Logic and Proofs → Debugging and Algorithms

### 1. Proof by Contradiction → Debugging "Impossible States"

The most powerful thinking pattern when a bug occurs:

> "If this code is correct, the value at this point must be X. But looking at the logs, it's Y. **Contradiction**. Therefore there is a bug in this code path."

This is **proof by contradiction**. Specifically:

```
[Debugging Contradiction Pattern]

1. Assumption: "Function A works correctly"
2. If the assumption is true: A's output should always be positive (per spec)
3. But a negative value was found in the logs
4. Contradiction → Assumption is false → A has a bug
5. Investigate inside A, applying the same pattern recursively
```

### 2. Contrapositive → Conditional Refactoring

$$P \Rightarrow Q \;\equiv\; \neg Q \Rightarrow \neg P$$

Complex conditionals often become clearer when flipped to the contrapositive:

```csharp
// Original (direct): "If valid target, deal damage"
if (target != null && target.IsAlive && !target.IsInvincible)
{
    ApplyDamage(target);
}

// Refactored by contrapositive: "Filter out cases where damage can't be dealt" (Guard Clause)
if (target == null) return;
if (!target.IsAlive) return;
if (target.IsInvincible) return;
ApplyDamage(target);
```

Mathematically equivalent, but **readability and maintainability** improve dramatically.

### 3. Mathematical Induction → Correctness of Recursive Algorithms

Verifying that a recursive algorithm works correctly is **mathematical induction itself**.

```csharp
// Fractal tree generation
void GenerateBranch(Vector3 start, float length, int depth)
{
    // Base case: terminate when depth == 0
    if (depth <= 0) return;  // Check P(0)

    // Inductive step:
    // Assume "correctly drawn up to depth-1" (induction hypothesis)
    // Show correctness at depth

    Vector3 end = start + direction * length;
    DrawLine(start, end);

    // P(k) → P(k+1): recursive call with smaller depth
    GenerateBranch(end, length * 0.7f, depth - 1);  // left
    GenerateBranch(end, length * 0.7f, depth - 1);  // right
}
```

> **How to prove a recursion doesn't loop infinitely:** Show that the base case is always reachable and that some value (here, depth) **strictly decreases** with each call. This is a **termination proof**.
{: .prompt-tip}

### 4. Constructive Proof → Procedural Generation

"Such a dungeon exists" is non-constructive. In games, we need the constructive proof: **"here's how to build it."**

```
[Constructive Thinking for Dungeon Generation]

Claim: "A dungeon where all rooms are connected can be generated"

Constructive proof:
1. Place one room (base case)
2. Select an existing room and connect a new room at an adjacent position (inductive step)
3. Repeat step 2 n-1 times to create a dungeon with n connected rooms

→ This proof itself is the algorithm!
```

<br>

---

## XII. Bijection/Countability → Hashing, Serialization, ID Systems

### 1. Bijection = Perfect Mapping System

When designing **ID systems** in games, the concept of bijection is key:

```csharp
// Entity ID → Entity Object mapping must be a bijection because:
// Injection: Two Entities must not be referenced by the same ID (collision prevention)
// Surjection: Every Entity must have an ID (no missing entries)
Dictionary<int, Entity> entityMap;  // Must guarantee bijection
```

**If injection breaks:** Same key for two objects → one disappears (hash collision)
**If surjection breaks:** Object without ID → unmanageable (memory leak)

### 2. Hash Function = A Function That Sacrifices Surjectivity for Speed

$$h: \text{Large set (keys)} \to \text{Small set (buckets)}$$

Since the number of possible keys $\gg$ number of buckets, collisions are inevitable by the **Pigeonhole Principle**.

> **Pigeonhole Principle:** If $n+1$ items are placed into $n$ boxes, at least one box contains 2 or more items. Simple but a powerful tool used throughout computer science.
{: .prompt-info}

### 3. Countable/Uncountable → Searchability of State Spaces

| State Space | Countability | Meaning in Games |
|----------|--------|--------------|
| Legal moves in chess | Countable (finite) | Complete search possible (theoretically) |
| Legal moves in Go | Countable (finite but enormous) | Complete search impossible → MCTS, AI needed |
| Continuous physics simulation | Uncountable | Discretization required → Fixed timestep |

> The reason physics engines use `FixedUpdate`: continuous (uncountable) time must be converted to discrete (countable) steps for computation to be possible. This is **discretization**, the core idea of numerical analysis.
{: .prompt-warning}

<br>

---

## XIII. Axiomatic Thinking → Game Design Principles

### "Axioms of Game Design" = Game Rules

Just as Euclidean geometry derived all theorems from 5 axioms, all actions and outcomes in a game are derived from **rules (axioms)**.

```
[Game Axiom System Example - Card Game]

Axiom 1: A deck is an ordered set of cards
Axiom 2: A player draws exactly 1 card per turn
Axiom 3: Maximum hand size is 7
Axiom 4: Mana increases by 1 at the start of each turn, maximum 10

→ Theorem: "On turn 8, the player's maximum mana is 8" (deduced from Axiom 4)
→ Theorem: "If no cards are played for 7 turns, the player has 7 cards" (Axioms 2, 3)
→ Bug detection: "Has 10 mana but played an 11-mana card" → Axiom violation → Bug
```

### Consistency of Axioms = Game Balance

Just as Euclid's 5 axioms must not contradict each other, **game rules must not contradict each other.**

```
Rule A: "No damage is taken during invincibility buff"
Rule B: "Poison status deals 5% HP per second"

Q: What happens when invincibility + poison are active simultaneously?
→ Axiom conflict! A priority rule (additional axiom) must be added, or one must be modified.
```

> Most "corner case bugs" found in games arise from **contradictions between rules (axioms)**. Just as mathematicians verify the consistency of axiom systems, game designers must verify the consistency of their rules.
{: .prompt-danger}

### Independence of Axioms = Modularity

Just as Euclid's 5th postulate was independent of the other 4, **a good game system has independent subsystems**.

- Changing the combat system doesn't break the inventory → Independent
- Changing movement speed affects jump height → Dependent (high coupling)

This is precisely the mathematical origin of **loose coupling** in software engineering.

<br>

---

## XIV. Practical Cheat Sheet: Symbol Decoding Table for Papers

The first thing that blocks you when opening a graduate paper is the **symbols**.

| Symbol | Reading | Meaning |
|--------|---------|---------|
| $\forall$ | for all | For every ~ |
| $\exists$ | there exists | There exists ~ |
| $\exists!$ | there exists unique | There uniquely exists |
| $\in$ | element of | Belongs to ~ |
| $\subseteq$ | subset of | Subset of ~ |
| $\subset$ | proper subset | Proper subset of ~ |
| $\implies$ ($\Rightarrow$) | implies | If ~ then |
| $\iff$ ($\Leftrightarrow$) | if and only if (iff) | If and only if (necessary and sufficient) |
| $:=$ or $\triangleq$ | defined as | Is defined as ~ |
| $\approx$ | approximately | Approximately equal |
| $\propto$ | proportional to | Proportional to ~ |
| $\sim$ | distributed as / equivalent | Follows the distribution of ~ / equivalent |
| $\|x\|$ | norm of x | Magnitude (norm) of x |
| $\langle x, y \rangle$ | inner product | Inner product of x and y |
| $\nabla$ | nabla (gradient) | Gradient |
| $\partial$ | partial | Partial derivative |
| $\sum$ | summation | Sum |
| $\prod$ | product | Product |
| $\int$ | integral | Integral |
| $\circ$ | composition | Composition ($f \circ g = f(g(\cdot))$) |
| $\mapsto$ | maps to | Maps to ~ ($x \mapsto x^2$) |
| $\mathbb{E}[X]$ | expectation | Expected value |
| $\Pr(A)$ or $P(A)$ | probability | Probability |
| s.t. | subject to | Subject to the condition ~ |
| w.r.t. | with respect to | With respect to ~ |
| i.i.d. | independently and identically distributed | Independent and identically distributed |
| a.s. | almost surely | Almost surely (probability 1) |
| w.l.o.g. | without loss of generality | Without loss of generality |
| QED or $\blacksquare$ | quod erat demonstrandum | End of proof |

### Decoding Common Paper Sentence Structures

```
Paper: "Let ε > 0 be given. Then ∃ δ > 0 s.t. ∀ x ∈ X,
       ‖x - a‖ < δ ⟹ ‖f(x) - f(a)‖ < ε."

Decoded: "Given any positive number ε, there exists a positive δ such that
         for all elements x in X, if the distance between x and a is less than δ,
         then the distance between f(x) and f(a) is also less than ε."

One-line summary: "f is continuous at point a."
```

```
Paper: "∀ η > 0, the sequence {x_n} converges to x* a.s.,
       i.e., Pr(lim_{n→∞} x_n = x*) = 1."

Decoded: "The sequence {x_n} converges to x* almost surely.
         That is, the probability that x_n converges to x* is 1."
```

<br>

---

## Questions for Next Time

- What is the mathematical definition of the set of natural numbers? (Some might say $1, 2, 3, \cdots$, but isn't using '$\cdots$' problematic?)
- Why does $1 + 1 = 2$? (If you want to protest "why ask something so obvious," can you explain it convincingly?)
- Why does $(-1) \times (-1) = 1$?

<br>

---

## References

- [YouTube lecture on expected value](https://www.youtube.com/watch?v=DLzw99LIwG0)
- Lecture Note 1 (Sets, Propositions, and Axioms) - Based on handwritten notes
- Halmos, P. - *Naive Set Theory* (A classic introduction to set theory)
- Velleman, D. - *How to Prove It* (A textbook on proof techniques)
- Munkres, J. - *Topology* (Standard topology textbook)
