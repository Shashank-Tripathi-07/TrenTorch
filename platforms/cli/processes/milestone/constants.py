"""Static milestone data: which scripts back each milestone, name aliases,
achievement copy, and the export symbols each module is expected to expose.

Pure data, no logic, so every other file in this package (and workflow.py,
dev/test.py, which reach in for MILESTONE_SCRIPTS directly) can import from
here without pulling in MilestoneSystem or MilestoneCommand.
"""

# Name aliases for milestone IDs (allows `tren milestone run perceptron`)
MILESTONE_ALIASES = {
    "perceptron": "01",
    "xor": "02",
    "mlp": "03",
    "cnn": "04",
    "transformer": "05",
    "mlperf": "06",
    "olympics": "06",
}

# Milestone-to-script mapping for tren milestone run command
MILESTONE_SCRIPTS = {
    "01": {
        "id": "01",
        "name": "Perceptron (1958)",
        "year": 1958,
        "title": "Frank Rosenblatt's First Neural Network",
        "script": "data/milestones/01_1958_perceptron/01_rosenblatt_forward.py",
        "required_modules": [1, 2, 3],  # Tensor, Activations, Layers (forward pass only)
        "description": "Build the first neural network (forward pass)",
        "historical_context": "Rosenblatt's perceptron proved machines could learn. Built on McCulloch & Pitts' 1943 paper 'A Logical Calculus of the Ideas Immanent in Nervous Activity' - the first mathematical model of an artificial neuron.",
        "emoji": "🧠",
    },
    "02": {
        "id": "02",
        "name": "XOR Crisis (1969)",
        "year": 1969,
        "title": "The Problem That Stalled AI",
        "script": "data/milestones/02_1969_xor/01_xor_crisis.py",
        "required_modules": [1, 2, 3],  # Just forward pass: Tensor, Activations, Layers
        "description": "Single-layer perceptron CANNOT solve XOR (75% max)",
        "historical_context": "Minsky & Papert proved limits of single-layer networks",
        "emoji": "🔀",
    },
    "03": {
        "id": "03",
        "name": "MLP Revival (1986)",
        "year": 1986,
        "title": "Backpropagation Breakthrough",
        "scripts": [
            {
                "name": "XOR Solved",
                "script": "data/milestones/02_1969_xor/02_xor_solved.py",
                "description": "Hidden layers + backprop SOLVE the impossible XOR problem!",
                "required_modules": [1, 2, 3, 4, 5, 6, 7, 8],  # Full training: Tensor through Training
            },
            {
                "name": "TinyDigits",
                "script": "data/milestones/03_1986_mlp/01_rumelhart_tinydigits.py",
                "description": "Scale up to real data - handwritten digit recognition",
                "required_modules": [1, 2, 3, 4, 5, 6, 7, 8],  # Full training infrastructure
            },
        ],
        "required_modules": [1, 2, 3, 4, 5, 6, 7, 8],  # Full training for XOR Solved
        "description": "Solve XOR with hidden layers, then train on real data",
        "historical_context": "Rumelhart, Hinton & Williams (Nature, 1986) ended the AI Winter",
        "emoji": "🎓",
    },
    "04": {
        "id": "04",
        "name": "CNN Revolution (1998)",
        "year": 1998,
        "title": "LeNet - Computer Vision Breakthrough",
        "default_part": 1,  # TinyDigits (no download required) is the default
        "scripts": [
            {
                "name": "TinyDigits",
                "script": "data/milestones/04_1998_cnn/01_lecun_tinydigits.py",
                "description": "Prove CNNs > MLPs on synthetic 8x8 digits (works offline)",
                "required_modules": [1, 2, 3, 4, 5, 6, 7, 8, 9],  # Full training + Convolutions
            },
            {
                "name": "CIFAR-10",
                "script": "data/milestones/04_1998_cnn/02_lecun_cifar10.py",
                "description": "Scale to natural images with YOUR DataLoader (requires download)",
                "required_modules": [1, 2, 3, 4, 5, 6, 7, 8, 9],  # Full training + Convolutions
            },
        ],
        "required_modules": [1, 2, 3, 4, 5, 6, 7, 8, 9],  # Full training + Convolutions
        "description": "Build LeNet for digit recognition, then scale to natural images",
        "historical_context": "Yann LeCun's convolutional networks revolutionized computer vision",
        "emoji": "👁️",
    },
    "05": {
        "id": "05",
        "name": "Transformer Era (2017)",
        "year": 2017,
        "title": "Attention is All You Need",
        "script": "data/milestones/05_2017_transformer/01_vaswani_attention.py",
        "required_modules": [
            1,
            2,
            3,
            4,
            5,
            6,
            7,
            8,
            11,
            12,
            13,
        ],  # Full training + Embeddings, Attention, Transformers
        "description": "Prove attention works with sequence reversal",
        "historical_context": "Vaswani et al. revolutionized NLP",
        "emoji": "🤖",
    },
    "06": {
        "id": "06",
        "name": "MLPerf Benchmarks (2018)",
        "year": 2018,
        "title": "The Optimization Olympics",
        "scripts": [
            {
                "name": "Model Compression",
                "script": "data/milestones/06_2018_mlperf/01_optimization_olympics.py",
                "description": "Profiling + Quantization + Pruning on MLP",
                "required_modules": [
                    1,
                    2,
                    3,
                    4,
                    5,
                    6,
                    7,
                    8,
                    14,
                    15,
                    16,
                    17,
                    18,
                    19,
                ],  # Full training + Optimization tier
            },
            {
                "name": "Generation Speedup",
                "script": "data/milestones/06_2018_mlperf/02_generation_speedup.py",
                "description": "KV Caching for 10x faster Transformer",
                "required_modules": [
                    1,
                    2,
                    3,
                    4,
                    5,
                    6,
                    7,
                    8,
                    11,
                    12,
                    14,
                    18,
                ],  # Full training + Embeddings + Attention + Profiler + Memoization (18)
            },
        ],
        "required_modules": [
            1,
            2,
            3,
            4,
            5,
            6,
            7,
            8,
            11,
            12,
            14,
            15,
            16,
            17,
            18,
            19,
        ],  # Full default run: optimization + generation speedup parts
        "description": "Compress and accelerate your neural network",
        "historical_context": "MLPerf standardized ML benchmarks",
        "emoji": "🏆",
    },
}

# "What makes this special" bullets, tailored per milestone's required_modules
# (01/02 are forward-pass only, so they can't claim "Every gradient: YOUR
# autograd" the way later milestones do).
MILESTONE_ACHIEVEMENT_HIGHLIGHTS = {
    "01": [
        "Every line of code: YOUR implementations",
        "Every tensor operation: YOUR Tensor class",
        "Every forward pass: YOUR Layers (no autograd needed yet)",
    ],
    "02": [
        "Every line of code: YOUR implementations",
        "Every tensor operation: YOUR Tensor class",
        "The exact limitation Minsky & Papert proved in 1969",
    ],
    "03": [
        "Every line of code: YOUR implementations",
        "Every tensor operation: YOUR Tensor class",
        "Every gradient: YOUR autograd",
    ],
    "04": [
        "Every line of code: YOUR implementations",
        "Every convolution: YOUR Conv2d",
        "Every gradient: YOUR autograd",
    ],
    "05": [
        "Every line of code: YOUR implementations",
        "Every attention weight: YOUR MultiHeadAttention",
        "Every gradient: YOUR autograd",
    ],
    "06": [
        "Every line of code: YOUR implementations",
        "Every byte saved: YOUR quantization and compression",
        "Every gradient: YOUR autograd",
    ],
}


MODULE_EXPORT_CHECKS = {
    1: [("trentorch", "Tensor"), ("trentorch.core.tensor", "Tensor")],
    2: [("trentorch", "ReLU"), ("trentorch.core.activations", "ReLU")],
    3: [("trentorch", "Linear"), ("trentorch.core.layers", "Linear")],
    4: [("trentorch", "CrossEntropyLoss"), ("trentorch.core.losses", "CrossEntropyLoss")],
    5: [("trentorch", "DataLoader"), ("trentorch.core.dataloader", "DataLoader")],
    6: [("trentorch", "enable_autograd"), ("trentorch.core.autograd", "enable_autograd")],
    7: [("trentorch", "SGD"), ("trentorch.core.optimizers", "SGD")],
    8: [("trentorch", "Trainer"), ("trentorch.core.training", "Trainer")],
    9: [("trentorch", "Conv2d"), ("trentorch.core.spatial", "Conv2d")],
    10: [("trentorch", "CharTokenizer"), ("trentorch.core.tokenization", "CharTokenizer")],
    11: [("trentorch", "Embedding"), ("trentorch.core.embeddings", "Embedding")],
    12: [("trentorch", "MultiHeadAttention"), ("trentorch.core.attention", "MultiHeadAttention")],
    13: [("trentorch", "TransformerBlock"), ("trentorch.core.transformers", "TransformerBlock")],
    14: [("trentorch", "Profiler"), ("trentorch.perf.profiling", "Profiler")],
    15: [("trentorch", "Quantizer"), ("trentorch.perf.quantization", "Quantizer")],
    16: [("trentorch", "Compressor"), ("trentorch.perf.compression", "Compressor")],
    17: [("trentorch", "vectorized_matmul"), ("trentorch.perf.acceleration", "vectorized_matmul")],
    18: [("trentorch", "KVCache"), ("trentorch.perf.memoization", "KVCache")],
    19: [("trentorch.perf.benchmarking", "Benchmark")],
    20: [("trentorch", "olympics")],
}
