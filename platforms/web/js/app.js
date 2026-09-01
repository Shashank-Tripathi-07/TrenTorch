/**
 * TrenTorch Companion Visualizer & Live Bridge
 */

// Register PWA Service Worker
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(err => {
      console.warn('SW registration skipped:', err);
    });
  });
}

// Global Application State
const State = {
  activeTab: 'autograd',
  dag: null,
  dagAnimation: { stage: 'idle', progress: 0, timer: null },
  dagTransform: { x: 40, y: 30, scale: 1.0, isDragging: false, startX: 0, startY: 0 },
  modules: [],
  milestones: [],
  systemStatus: null,
  activeTestStream: null,
  digitGrid: Array(28 * 28).fill(0),
  isDrawing: false,
};

// ---------------- INITIALIZATION ----------------

document.addEventListener('DOMContentLoaded', () => {
  initNavigation();
  initAutogradCanvas();
  initAttentionHeatmap();
  initConvVisualizer();
  initDigitCanvas();
  fetchSystemStatus();
  fetchModules();
  fetchMilestones();
  fetchBenchmarks();
});

function initNavigation() {
  const navBtns = document.querySelectorAll('.nav-btn');
  navBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const target = btn.getAttribute('data-tab');
      switchTab(target);
    });
  });
}

function switchTab(tabId) {
  State.activeTab = tabId;
  document.querySelectorAll('.nav-btn').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-tab') === tabId);
  });
  document.querySelectorAll('.tab-pane').forEach(p => {
    p.classList.toggle('active', p.id === `tab-${tabId}`);
  });

  if (tabId === 'autograd') {
    renderDag();
  }
}

// ---------------- REST & STATUS FETCHING ----------------

async function fetchSystemStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    State.systemStatus = data;

    const pill = document.getElementById('headerStatusPill');
    if (pill) {
      pill.innerHTML = `
        <span class="status-dot"></span>
        <span>Python ${data.python_version}</span>
        <span style="color: var(--text-muted)">|</span>
        <span style="color: var(--accent-cyan)">${data.completed_count}/${data.total_modules} Modules</span>
      `;
    }
  } catch (err) {
    console.warn('Backend offline or standalone demo mode.');
  }
}

async function fetchModules() {
  try {
    const res = await fetch('/api/modules');
    const data = await res.json();
    State.modules = data.modules || [];
    renderModulesGrid();
  } catch (err) {
    console.warn('Failed to fetch modules:', err);
  }
}

async function fetchMilestones() {
  try {
    const res = await fetch('/api/milestones');
    const data = await res.json();
    State.milestones = data.milestones || [];
  } catch (err) {
    console.warn('Failed to fetch milestones:', err);
  }
}

async function fetchBenchmarks() {
  try {
    const res = await fetch('/api/benchmarks/quick');
    const data = await res.json();
    renderBenchmarks(data.benchmarks || []);
    const note = document.getElementById('benchmarkNote');
    if (note && data.note) note.innerText = data.note;
  } catch (err) {
    console.warn('Failed to fetch benchmarks:', err);
  }
}

// ---------------- 1. AUTOGRAD COMPUTATIONAL DAG VISUALIZER ----------------

function initAutogradCanvas() {
  const canvas = document.getElementById('dagCanvas');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');

  function resizeCanvas() {
    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = rect.width * window.devicePixelRatio;
    canvas.height = rect.height * window.devicePixelRatio;
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    renderDag();
  }

  window.addEventListener('resize', resizeCanvas);
  setTimeout(resizeCanvas, 50);

  // Pan & Zoom
  canvas.addEventListener('mousedown', e => {
    State.dagTransform.isDragging = true;
    State.dagTransform.startX = e.clientX - State.dagTransform.x;
    State.dagTransform.startY = e.clientY - State.dagTransform.y;
    canvas.style.cursor = 'grabbing';
  });

  window.addEventListener('mousemove', e => {
    if (!State.dagTransform.isDragging) return;
    State.dagTransform.x = e.clientX - State.dagTransform.startX;
    State.dagTransform.y = e.clientY - State.dagTransform.startY;
    renderDag();
  });

  window.addEventListener('mouseup', () => {
    State.dagTransform.isDragging = false;
    canvas.style.cursor = 'grab';
  });

  // Action Buttons
  document.getElementById('btnDagForward')?.addEventListener('click', runDagForward);
  document.getElementById('btnDagBackward')?.addEventListener('click', runDagBackward);
  document.getElementById('btnDagReset')?.addEventListener('click', resetDag);

  // Initialize Default Graph Layout
  initDagLayout();
}

function initDagLayout() {
  State.dag = {
    nodes: [
      { id: 'x', label: 'x', sub: 'Input [4, 8]', type: 'input', x: 80, y: 120, val: '0.42', grad: null },
      { id: 'w1', label: 'W₁', sub: 'Param [8, 16]', type: 'param', x: 80, y: 240, val: '0.18', grad: '-0.042' },
      { id: 'b1', label: 'b₁', sub: 'Bias [16]', type: 'param', x: 80, y: 360, val: '0.00', grad: '0.015' },
      { id: 'z1', label: 'MatMul + Add', sub: 'LinearForward', type: 'op', x: 300, y: 220, val: '0.68', grad: '-0.120' },
      { id: 'a1', label: 'ReLU', sub: 'Activation', type: 'op', x: 480, y: 220, val: '0.68', grad: '0.084' },
      { id: 'w2', label: 'W₂', sub: 'Param [16, 2]', type: 'param', x: 480, y: 360, val: '0.55', grad: '0.312' },
      { id: 'b2', label: 'b₂', sub: 'Bias [2]', type: 'param', x: 480, y: 100, val: '0.00', grad: '0.440' },
      { id: 'logits', label: 'Logits', sub: 'Head [4, 2]', type: 'op', x: 680, y: 220, val: '1.24', grad: '0.220' },
      { id: 'targets', label: 'y (Targets)', sub: 'Ground Truth', type: 'input', x: 680, y: 360, val: '1.00', grad: null },
      { id: 'loss', label: 'MSE Loss', sub: 'Scalar Output', type: 'loss', x: 880, y: 280, val: '0.1428', grad: '1.0000' },
    ],
    edges: [
      { from: 'x', to: 'z1' },
      { from: 'w1', to: 'z1' },
      { from: 'b1', to: 'z1' },
      { from: 'z1', to: 'a1' },
      { from: 'a1', to: 'logits' },
      { from: 'w2', to: 'logits' },
      { from: 'b2', to: 'logits' },
      { from: 'logits', to: 'loss' },
      { from: 'targets', to: 'loss' },
    ]
  };
}

function renderDag() {
  const canvas = document.getElementById('dagCanvas');
  if (!canvas || !State.dag) return;

  const ctx = canvas.getContext('2d');
  const width = canvas.width / window.devicePixelRatio;
  const height = canvas.height / window.devicePixelRatio;

  ctx.clearRect(0, 0, width, height);
  ctx.save();
  ctx.translate(State.dagTransform.x, State.dagTransform.y);
  ctx.scale(State.dagTransform.scale, State.dagTransform.scale);

  // Draw Grid Background
  drawCanvasGrid(ctx, -State.dagTransform.x, -State.dagTransform.y, width, height);

  // 1. Draw Edges
  State.dag.edges.forEach(edge => {
    const fromNode = State.dag.nodes.find(n => n.id === edge.from);
    const toNode = State.dag.nodes.find(n => n.id === edge.to);
    if (!fromNode || !toNode) return;

    ctx.beginPath();
    const startX = fromNode.x + 130;
    const startY = fromNode.y + 35;
    const endX = toNode.x;
    const endY = toNode.y + 35;

    const cp1x = startX + (endX - startX) * 0.5;
    const cp1y = startY;
    const cp2x = startX + (endX - startX) * 0.5;
    const cp2y = endY;

    ctx.moveTo(startX, startY);
    ctx.bezierCurveTo(cp1x, cp1y, cp2x, cp2y, endX, endY);

    if (State.dagAnimation.stage === 'forward') {
      ctx.strokeStyle = '#38bdf8';
      ctx.lineWidth = 2.5;
      ctx.shadowColor = '#38bdf8';
      ctx.shadowBlur = 10;
    } else if (State.dagAnimation.stage === 'backward') {
      ctx.strokeStyle = '#f59e0b';
      ctx.lineWidth = 2.5;
      ctx.shadowColor = '#f59e0b';
      ctx.shadowBlur = 10;
    } else {
      ctx.strokeStyle = '#334155';
      ctx.lineWidth = 1.5;
      ctx.shadowBlur = 0;
    }
    ctx.stroke();
    ctx.shadowBlur = 0;
  });

  // 2. Draw Nodes
  State.dag.nodes.forEach(node => {
    drawDagNode(ctx, node);
  });

  ctx.restore();
}

function drawCanvasGrid(ctx, x, y, w, h) {
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.02)';
  ctx.lineWidth = 1;
  const gridSize = 40;
  const startX = Math.floor(x / gridSize) * gridSize;
  const startY = Math.floor(y / gridSize) * gridSize;

  for (let gx = startX; gx < x + w + gridSize; gx += gridSize) {
    ctx.beginPath();
    ctx.moveTo(gx, y);
    ctx.lineTo(gx, y + h);
    ctx.stroke();
  }
  for (let gy = startY; gy < y + h + gridSize; gy += gridSize) {
    ctx.beginPath();
    ctx.moveTo(x, gy);
    ctx.lineTo(x + w, gy);
    ctx.stroke();
  }
}

function drawDagNode(ctx, node) {
  const nodeWidth = 130;
  const nodeHeight = 70;
  const radius = 10;

  // Node Background
  ctx.fillStyle = '#0f1422';
  ctx.beginPath();
  ctx.roundRect(node.x, node.y, nodeWidth, nodeHeight, radius);
  ctx.fill();

  // Node Border
  let strokeColor = '#334155';
  if (node.type === 'param') strokeColor = '#8b5cf6';
  else if (node.type === 'op') strokeColor = '#38bdf8';
  else if (node.type === 'loss') strokeColor = '#f59e0b';

  ctx.strokeStyle = strokeColor;
  ctx.lineWidth = 1.5;
  ctx.stroke();

  // Node Label
  ctx.fillStyle = '#f8fafc';
  ctx.font = 'bold 13px Inter, sans-serif';
  ctx.fillText(node.label, node.x + 12, node.y + 24);

  // Node Subtitle / Op
  ctx.fillStyle = '#94a3b8';
  ctx.font = '10px JetBrains Mono, monospace';
  ctx.fillText(node.sub, node.x + 12, node.y + 42);

  // Forward Value Badge
  if (State.dagAnimation.stage !== 'idle') {
    ctx.fillStyle = '#0284c7';
    ctx.font = '10px JetBrains Mono, monospace';
    ctx.fillText(`val: ${node.val}`, node.x + 12, node.y + 58);
  }

  // Backward Grad Badge
  if (State.dagAnimation.stage === 'backward' && node.grad) {
    ctx.fillStyle = '#f59e0b';
    ctx.font = 'bold 10px JetBrains Mono, monospace';
    ctx.fillText(`grad: ${node.grad}`, node.x + 68, node.y + 24);
  }
}

function runDagForward() {
  State.dagAnimation.stage = 'forward';
  document.getElementById('dagStatusInfo').innerText = '▶ Forward pass: activations flow from inputs to the loss node (illustrative values).';
  renderDag();
}

function runDagBackward() {
  State.dagAnimation.stage = 'backward';
  document.getElementById('dagStatusInfo').innerText = '⚡ Backward pass: gradients flow back via the chain rule (illustrative values).';
  renderDag();
}

function resetDag() {
  State.dagAnimation.stage = 'idle';
  document.getElementById('dagStatusInfo').innerText = 'Illustrative graph. Click Forward or Backward pass to trace the flow.';
  renderDag();
}

// ---------------- 2. ATTENTION HEATMAP & CONV2D VISUALIZER ----------------

function initAttentionHeatmap() {
  const container = document.getElementById('attentionGrid');
  if (!container) return;

  const tokens = ['The', 'robot', 'learned', 'to', 'think', 'deeply'];
  const numTokens = tokens.length;

  // Fixed toy embeddings (d = 4). Q = K = these vectors, so the heatmap is a
  // real causal softmax(QKᵀ / √d), computed here rather than randomised.
  const embeddings = [
    [0.9, 0.1, 0.0, 0.2],
    [0.2, 0.8, 0.1, 0.0],
    [0.1, 0.3, 0.9, 0.2],
    [0.0, 0.1, 0.2, 0.7],
    [0.3, 0.2, 0.6, 0.4],
    [0.2, 0.5, 0.3, 0.8],
  ];
  const d = embeddings[0].length;
  const scale = Math.sqrt(d);
  const dot = (a, b) => a.reduce((s, v, k) => s + v * b[k], 0);

  // Row-wise causal softmax of the score matrix.
  const attn = embeddings.map((qi, i) => {
    const scores = embeddings.map((kj, j) => (j > i ? -Infinity : dot(qi, kj) / scale));
    const max = Math.max(...scores.filter(Number.isFinite));
    const exps = scores.map(s => (Number.isFinite(s) ? Math.exp(s - max) : 0));
    const sum = exps.reduce((s, v) => s + v, 0) || 1;
    return exps.map(v => v / sum);
  });

  container.style.gridTemplateColumns = `repeat(${numTokens + 1}, auto)`;

  let html = `<div class="heatmap-cell" style="background:transparent"></div>`;
  tokens.forEach(t => {
    html += `<div class="heatmap-cell" style="background:transparent; color:var(--accent-cyan); font-weight:bold">${t}</div>`;
  });

  for (let i = 0; i < numTokens; i++) {
    html += `<div class="heatmap-cell" style="background:transparent; color:var(--accent-cyan); font-weight:bold">${tokens[i]}</div>`;
    for (let j = 0; j < numTokens; j++) {
      const weight = attn[i][j];
      const alpha = weight.toFixed(2);
      const bg = `rgba(139, 92, 246, ${Math.min(1, weight)})`;
      const textCol = weight > 0.4 ? '#ffffff' : '#94a3b8';

      html += `<div class="heatmap-cell" style="background:${bg}; color:${textCol}" title="Attention (${tokens[i]} → ${tokens[j]}): ${alpha}">
        ${alpha}
      </div>`;
    }
  }

  container.innerHTML = html;
}

// A fixed 6x6 input tensor so the Conv2D view is deterministic between renders.
const CONV_INPUT = [
  [1, 2, 0, 3, 1, 0],
  [0, 4, 2, 1, 0, 2],
  [3, 1, 5, 2, 1, 3],
  [2, 0, 1, 4, 2, 1],
  [1, 3, 2, 0, 5, 0],
  [0, 1, 4, 2, 1, 2],
];

function initConvVisualizer() {
  const container = document.getElementById('convGrid');
  if (!container) return;

  // 6x6 input tensor with the active 3x3 receptive field (rows/cols 1..3) highlighted.
  container.style.gridTemplateColumns = 'repeat(6, 40px)';
  let html = '';
  for (let r = 0; r < 6; r++) {
    for (let c = 0; c < 6; c++) {
      const inKernel = (r >= 1 && r <= 3 && c >= 1 && c <= 3);
      const bg = inKernel ? 'rgba(56, 189, 248, 0.4)' : 'rgba(255, 255, 255, 0.05)';
      const border = inKernel ? '1px solid var(--accent-cyan)' : '1px solid rgba(255, 255, 255, 0.08)';
      html += `<div class="heatmap-cell" style="width:38px; height:38px; background:${bg}; border:${border}; color:#e2e8f0">${CONV_INPUT[r][c]}</div>`;
    }
  }
  container.innerHTML = html;
}

// ---------------- 3. MILESTONE PLAYGROUND (LENET DIGIT CANVAS) ----------------

function initDigitCanvas() {
  const canvas = document.getElementById('digitCanvas');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#000000';
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  function draw(e) {
    if (!State.isDrawing) return;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.arc(x, y, 14, 0, Math.PI * 2);
    ctx.fill();
  }

  canvas.addEventListener('mousedown', e => {
    State.isDrawing = true;
    draw(e);
  });

  window.addEventListener('mousemove', draw);
  window.addEventListener('mouseup', () => {
    State.isDrawing = false;
  });

  document.getElementById('btnClearCanvas')?.addEventListener('click', () => {
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  });

  renderDigitPlaceholder();
}

// Model inference is not wired into the companion yet, so show an honest
// placeholder instead of fabricated per-digit confidence scores.
function renderDigitPlaceholder() {
  const barsContainer = document.getElementById('digitProbBars');
  if (barsContainer) {
    barsContainer.innerHTML = `
      <div class="log-line dim" style="font-family: var(--font-mono); font-size: 0.8rem;">
        LeNet-5 inference is not connected to the companion yet.<br>
        Export Module 09 (Conv2D) and Milestone 04 to enable it.
      </div>
    `;
  }
  const predBadge = document.getElementById('predictedDigitBadge');
  if (predBadge) {
    predBadge.innerText = '—';
  }
}

// ---------------- 4. MODULES MATRIX & TEST RUNNER ----------------

function renderModulesGrid() {
  const container = document.getElementById('modulesMatrix');
  if (!container) return;

  container.innerHTML = State.modules.map(mod => {
    const badgeClass = mod.status;
    const badgeLabel = mod.status === 'completed' ? '✓ DONE' : (mod.status === 'in_progress' ? '▶ IN PROGRESS' : '○ PENDING');

    return `
      <div class="module-card">
        <div class="module-top">
          <span class="mod-num">Module ${mod.id}</span>
          <span class="mod-badge ${badgeClass}">${badgeLabel}</span>
        </div>
        <div class="mod-title">${mod.title}</div>
        <div class="mod-desc">${mod.description}</div>
        <div style="display: flex; gap: 8px;">
          <button class="btn btn-primary" style="padding: 6px 12px; font-size: 0.78rem" onclick="runModuleTest('${mod.id}')">
            🧪 Run Tests
          </button>
          <button class="btn btn-secondary" style="padding: 6px 12px; font-size: 0.78rem" onclick="completeModule('${mod.id}')">
            🚀 Export
          </button>
        </div>
      </div>
    `;
  }).join('');
}

function runModuleTest(moduleId) {
  const term = document.getElementById('terminalOutput');
  if (!term) return;

  // Switch to terminal tab/view and clear
  term.innerHTML = `<div class="log-line info">⚡ Starting pytest for Module ${moduleId}...</div>\n`;

  if (State.activeTestStream) {
    State.activeTestStream.close();
  }

  const evtSource = new EventSource(`/api/modules/${moduleId}/test/stream`);
  State.activeTestStream = evtSource;

  evtSource.addEventListener('output', e => {
    const data = JSON.parse(e.data);
    const lineDiv = document.createElement('div');
    lineDiv.className = 'log-line';
    if (data.line.includes('PASSED')) lineDiv.className += ' success';
    else if (data.line.includes('FAILED') || data.line.includes('ERROR')) lineDiv.className += ' error';
    lineDiv.innerText = data.line;
    term.appendChild(lineDiv);
    term.scrollTop = term.scrollHeight;
  });

  evtSource.addEventListener('end', e => {
    const data = JSON.parse(e.data);
    const lineDiv = document.createElement('div');
    lineDiv.className = data.passed ? 'log-line success' : 'log-line error';
    lineDiv.innerText = `\n✔ Test suite completed with exit code: ${data.exit_code}`;
    term.appendChild(lineDiv);
    evtSource.close();
    fetchModules();
    fetchSystemStatus();
  });

  evtSource.addEventListener('error', () => {
    const lineDiv = document.createElement('div');
    lineDiv.className = 'log-line error';
    lineDiv.innerText = '\n❌ Stream connection closed or error encountered.';
    term.appendChild(lineDiv);
    evtSource.close();
  });
}

async function completeModule(moduleId) {
  const term = document.getElementById('terminalOutput');
  if (term) {
    term.innerHTML = `<div class="log-line info">🚀 Exporting Module ${moduleId} to data/trentorch...</div>\n`;
  }
  try {
    const res = await fetch(`/api/modules/${moduleId}/complete`, { method: 'POST' });
    const data = await res.json();
    if (term) {
      const lineDiv = document.createElement('div');
      lineDiv.className = data.success ? 'log-line success' : 'log-line error';
      lineDiv.innerText = data.success ? `✔ Module ${moduleId} exported successfully!` : `❌ Export failed:\n${data.stderr}`;
      term.appendChild(lineDiv);
    }
    fetchModules();
    fetchSystemStatus();
  } catch (err) {
    if (term) {
      term.innerHTML += `<div class="log-line error">❌ Request error: ${err}</div>`;
    }
  }
}

// ---------------- 5. BENCHMARK COMPARISONS ----------------

function renderBenchmarks(benchmarks) {
  const tableBody = document.getElementById('benchmarkTableBody');
  if (!tableBody) return;

  tableBody.innerHTML = benchmarks.map(b => {
    const tren = (b.trentorch_time === null || b.trentorch_time === undefined)
      ? '<span style="color: var(--text-muted)">not exported</span>'
      : `${b.trentorch_time} ${b.unit}`;
    return `
    <tr>
      <td style="font-weight: 600">${b.op}</td>
      <td style="font-family: var(--font-mono); color: var(--accent-cyan)">${b.numpy_time} ${b.unit}</td>
      <td style="font-family: var(--font-mono); color: var(--accent-emerald); font-weight: bold">${tren}</td>
      <td style="font-family: var(--font-mono); color: var(--accent-amber)">${b.throughput_gflops} GFLOPS</td>
    </tr>
  `;
  }).join('');
}
