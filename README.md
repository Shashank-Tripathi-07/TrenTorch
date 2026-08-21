<div align="center">

<img src=".github/assets/trentorch-bolt.svg" width="120" height="120" alt="TrenTorch pulsing bolt mark" />

# Tren⚡Torch

### TinyTorch. On Steroids.

[![Python](https://img.shields.io/badge/python-3.10+-3776ab?logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Built From Scratch](https://img.shields.io/badge/dependencies-just%20NumPy-D4740C?logo=numpy&logoColor=white)](#what-youll-build)
[![Status](https://img.shields.io/badge/status-actively%20lifting-critical)](#current-status)

**Most people learn ML frameworks by importing them. We built ours by hand, then made it hit harder.**

[The Vision](#why-trentorch) · [20 Modules](#-20-progressive-modules) · [Milestones](#-historical-milestones)

</div>

---

> [!NOTE]
> **This is our implementation of [TinyTorch](https://mlsysbook.ai/tinytorch)** (Harvard CS249r), rebuilt in our own style and pushed further. Same bones, more muscle.

---

## Why TrenTorch?

Everyone wants to be an astronaut. Very few want to be the rocket scientist.

Everyone wants to train models, run inference, ship AI. Almost nobody wants to know how the framework under their feet actually works, line by line, tensor by tensor.

**We wanted to know. So we built one. Then we didn't stop at "good enough."**

### The Bricks 🧱

TinyTorch teaches the fundamentals. TrenTorch takes those same bricks and adds the reps: cleaner internals, sharper performance instincts, and an implementation pushed past the original spec wherever we saw the chance.

- **Small enough to read in one sitting** - every op traceable back to raw NumPy
- **Big enough to actually flex** - the real architecture real frameworks run on
- **Ours** - rebuilt, refactored, and hardened in our own hands

No black boxes. No `import torch`. Just the machinery, exposed.

<div align="center">
<img src=".github/assets/skunkworks-log.svg" width="100%" alt="Night-shift engineering log: coffee stains, a transpose bug found at 01:42, and a stamp reading built at 3 AM" />
</div>

---

## What You'll Build

A **complete ML framework**, built from zero. No single finish line, a set of missions you clear on the way there:

🎯 **Mission: Image** - we teach Image
- Real computer vision on standard benchmarks
- Conv2d, pooling, and CNNs, built entirely from scratch on NumPy
- Performance that holds its own against the frameworks it's built to demystify

🎯 **Mission: NLP** - we teach NLP
- Tokenization, embeddings, and multi-head attention, hand-rolled
- The groundwork every language model stands on

🎯 **Mission: LLM** - we teach LLM
- Full GPT-style transformer blocks, not a wrapper around someone else's
- Real self-attention, real language generation

🎯 **Mission: Inference** - we teach Inference
- Profiling, quantization, and acceleration, so your model doesn't just train, it runs
- KV-cache and memoization for the speed that production demands

🎯 **Mission: LLMOps** - we teach LLMOps
- Modern optimizers with learning rate scheduling: SGD, Adam, AdamW, Lion, Muon
- Competitive benchmarking and the capstone that ties it all together

**Zero PyTorch. Zero TensorFlow. Every line is ours.**

---

## Current Status

<table width="100%" style="width:100%">
  <thead>
    <tr>
      <th align="left" width="33%">Ready</th>
      <th align="left" width="33%">In Progress</th>
      <th align="left" width="34%">Coming Soon</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>✅ All 20 modules implemented</td>
      <td>🔧 Documentation polish</td>
      <td>📅 Community leaderboard</td>
    </tr>
    <tr>
      <td>✅ Module, CLI, integration, and milestone tests</td>
      <td>🔧 Edge case hardening</td>
      <td>📅 Binder/Colab support</td>
    </tr>
    <tr>
      <td>✅ <code>tito</code> CLI for workflows</td>
      <td>🔧 Performance tuning passes</td>
      <td>📅 More milestones beyond MLPerf</td>
    </tr>
    <tr>
      <td>✅ Historical milestone scripts</td>
      <td></td>
      <td></td>
    </tr>
  </tbody>
</table>

**Want to explore the code?** [Browse the repository structure](#repository-structure).

**Adventurous?** Local installation works, but bring a spotter. See the setup notes in [INSTRUCTOR.md](INSTRUCTOR.md).

---

## 🏗 20 Progressive Modules

Build your framework through four progressive parts:

<table width="100%" style="width:100%">
  <thead>
    <tr>
      <th align="left" width="20%">Part</th>
      <th align="left" width="15%">Modules</th>
      <th align="left" width="65%">What You Build</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td align="center"><b>I. Foundations</b></td>
      <td align="center">01-08</td>
      <td>Tensors, activations, layers, losses, dataloader, autograd, optimizers, training</td>
    </tr>
    <tr>
      <td align="center"><b>II. Vision</b></td>
      <td align="center">09</td>
      <td>Conv2d, CNNs for image classification</td>
    </tr>
    <tr>
      <td align="center"><b>III. Language</b></td>
      <td align="center">10-13</td>
      <td>Tokenization, embeddings, attention, transformers</td>
    </tr>
    <tr>
      <td align="center"><b>IV. Optimization</b></td>
      <td align="center">14-20</td>
      <td>Profiling, quantization, compression, acceleration, memoization, benchmarking, capstone</td>
    </tr>
  </tbody>
</table>

Each module asks one question: **"Can I build this from scratch, and can I build it well?"**

---

## 🏆 Historical Milestones

As you progress, you unlock recreations of landmark ML achievements, run on YOUR framework:

<table width="100%" style="width:100%">
  <thead>
    <tr>
      <th align="left" width="15%">Year</th>
      <th align="left" width="35%">Milestone</th>
      <th align="left" width="50%">Your Achievement</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td align="center"><b>1958</b></td>
      <td>Perceptron</td>
      <td>Binary classification with gradient descent</td>
    </tr>
    <tr>
      <td align="center"><b>1969</b></td>
      <td>XOR Crisis</td>
      <td>Multi-layer networks solve non-linear problems</td>
    </tr>
    <tr>
      <td align="center"><b>1986</b></td>
      <td>Backpropagation</td>
      <td>Multi-layer network training</td>
    </tr>
    <tr>
      <td align="center"><b>1998</b></td>
      <td>CNN Revolution</td>
      <td><b>Image classification with convolutions</b></td>
    </tr>
    <tr>
      <td align="center"><b>2017</b></td>
      <td>Transformer Era</td>
      <td>Language generation with self-attention</td>
    </tr>
    <tr>
      <td align="center"><b>2018+</b></td>
      <td>MLPerf</td>
      <td>Production-ready optimization</td>
    </tr>
  </tbody>
</table>

**Not toy demos.** Historically significant ML achievements, rebuilt with a framework we wrote ourselves.

---

## Learning Philosophy

```python
# Most courses:
import torch
model.fit(X, y)  # magic happens somewhere else

# TrenTorch:
# You implement every component
# You measure memory usage
# You optimize performance
# You own every layer of the stack
```

**Why build your own framework?**
- **Deep understanding** - know exactly what `loss.backward()` does, because you wrote it
- **Systems thinking** - memory, compute, and scaling stop being abstractions
- **Debugging at any depth** - fix problems at the model level or the tensor level
- **Production instincts** - the same patterns real ML systems run on

---

## Repository Structure

```text
TrenTorch/
├── src/                        # 💻 Python source files (edit here)
│   ├── 01_tensor/              # Module 01: Tensor operations from scratch
│   ├── 02_activations/         # Module 02: ReLU, Softmax activations
│   ├── 03_layers/              # Module 03: Linear layers, Module system
│   ├── 04_losses/              # Module 04: MSE, CrossEntropy losses
│   ├── 05_dataloader/          # Module 05: Efficient data pipelines
│   ├── 06_autograd/            # Module 06: Automatic differentiation
│   ├── 07_optimizers/          # Module 07: SGD, Adam optimizers
│   ├── 08_training/            # Module 08: Complete training loops
│   ├── 09_convolutions/        # Module 09: Conv2d, MaxPool2d, CNNs
│   ├── 10_tokenization/        # Module 10: Text processing
│   ├── 11_embeddings/          # Module 11: Token & positional embeddings
│   ├── 12_attention/           # Module 12: Multi-head attention
│   ├── 13_transformers/        # Module 13: Complete transformer blocks
│   ├── 14_profiling/           # Module 14: Performance analysis
│   ├── 15_quantization/        # Module 15: Model compression (precision reduction)
│   ├── 16_compression/         # Module 16: Pruning & distillation
│   ├── 17_acceleration/        # Module 17: Hardware optimization
│   ├── 18_memoization/         # Module 18: KV-cache/memoization
│   ├── 19_benchmarking/        # Module 19: Performance measurement
│   └── 20_capstone/            # Module 20: Complete ML systems
│
├── modules/                    # 📓 Generated notebooks (learn here)
│   └── ...                     # (20 module directories)
│
├── milestones/                 # 🏆 Historical ML evolution - prove what you built
│   ├── 01_1958_perceptron/
│   ├── 02_1969_xor/
│   ├── 03_1986_mlp/
│   ├── 04_1998_cnn/
│   ├── 05_2017_transformer/
│   └── 06_2018_mlperf/
│
├── tito/                       # 🎛️ CLI tool for streamlined workflows
│   ├── main.py                 # Entry point
│   ├── commands/                # Command modules
│   └── core/                   # Core utilities
│
├── tinytorch/                  # 📦 Generated package (import from here)
│   ├── core/                   # Core ML components
│   └── ...                     # The framework you built
│
└── tests/                      # ✅ Module, CLI, integration, and milestone tests
```

**Key workflow**: `src/*.py` → `modules/*.ipynb` → `tinytorch/*.py`

---

## Credit Where It's Due

TrenTorch is our implementation, built on the curriculum and foundation of [TinyTorch](https://mlsysbook.ai/tinytorch), created by [Prof. Vijay Janapa Reddi](https://vijay.seas.harvard.edu) and the [ML Systems Book](https://mlsysbook.ai) community at Harvard University. Full respect to the original project, we just wanted to take it further.

Related educational frameworks worth knowing about:
- [tinygrad](https://github.com/tinygrad/tinygrad) - George Hotz's minimalist framework
- [micrograd](https://github.com/karpathy/micrograd) - Andrej Karpathy's tiny autograd
- [MiniTorch](https://minitorch.github.io/) - Cornell's educational framework

We're addicted to making great software that runs (we're a bit of perfectionists ourselves) and is useful to humanity. This is our shot at making TinyTorch, but adding more stuff that is currently experimental and quite famous.

---

## Team Engineers

<table width="100%" style="width:100%">
  <tbody>
    <tr>
      <td align="center" valign="top" width="50%">
        <a href="https://github.com/Shashank-Tripathi-07"><img src="https://avatars.githubusercontent.com/Shashank-Tripathi-07?v=4" width="90px;" alt="Rocky"/></a>
        <br />
        <b>Rocky</b>
        <br />
        <sub>Debugs autograd for fun, ships before sunrise.</sub>
      </td>
      <td align="center" valign="top" width="50%">
        <a href="https://github.com/ShivtejG236"><img src="https://avatars.githubusercontent.com/ShivtejG236?v=4" width="90px;" alt="Shivtej Gaikwad"/></a>
        <br />
        <b>Shivtej Gaikwad</b>
        <br />
        <sub>IIT Guwahati. Shows up, ships, moves on to the next thing.</sub>
      </td>
    </tr>
  </tbody>
</table>

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

<div align="center">

<b>Start Small. Go Deep. Then Add Weight.</b>

</div>
