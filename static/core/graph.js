/**
 * CodeDNA Interactive Graph Visualizer
 * Physics-based force-directed simulation with Retina Canvas,
 * zoom/pan, drag-and-drop, blast-radius highlights, and module inspector.
 */
(function () {
  const container = document.getElementById("graph-viewport");
  const dataTag = document.getElementById("graph-data");
  if (!container || !dataTag) return;

  let graphData = { nodes: [], edges: [], cycles: [] };
  try {
    graphData = JSON.parse(dataTag.textContent);
  } catch (err) {
    console.error("Failed to parse graph data:", err);
  }

  const rawNodes = graphData.nodes || [];
  const rawEdges = graphData.edges || [];

  if (rawNodes.length === 0) {
    container.innerHTML = '<div style="padding: 40px; text-align: center; color: #64748b;">No modules to display. Upload a repository to view its dependency graph.</div>';
    return;
  }

  // Create Canvas
  const canvas = document.createElement("canvas");
  canvas.id = "canvas-graph";
  container.innerHTML = "";
  container.appendChild(canvas);

  const ctx = canvas.getContext("2d");
  let width = container.clientWidth || 800;
  let height = container.clientHeight || 520;
  let dpr = window.devicePixelRatio || 1;

  function resizeCanvas() {
    width = container.clientWidth || 800;
    height = container.clientHeight || 520;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = width + "px";
    canvas.style.height = height + "px";
    ctx.scale(dpr, dpr);
  }
  resizeCanvas();
  window.addEventListener("resize", () => {
    resizeCanvas();
    draw();
  });

  // Simulation State
  const nodeMap = {};
  const nodes = rawNodes.map((n, i) => {
    const angle = (2 * Math.PI * i) / rawNodes.length;
    const dist = Math.min(width, height) * 0.32;
    const obj = {
      ...n,
      x: width / 2 + dist * Math.cos(angle) + (Math.random() - 0.5) * 20,
      y: height / 2 + dist * Math.sin(angle) + (Math.random() - 0.5) * 20,
      vx: 0,
      vy: 0,
      radius: Math.max(9, Math.min(20, 8 + Math.sqrt(n.lines || 10) * 1.1 + (n.in_degree || 0) * 1.5)),
      isDragging: false,
    };
    nodeMap[n.id] = obj;
    return obj;
  });

  const edges = [];
  rawEdges.forEach(e => {
    if (nodeMap[e.from] && nodeMap[e.to]) {
      edges.push({ source: nodeMap[e.from], target: nodeMap[e.to] });
    }
  });

  // Color mapping
  function getNodeColor(node) {
    if (highlightState.affectedSet.has(node.id)) {
      return { fill: "#ef4444", border: "#fca5a5", glow: "rgba(239, 68, 68, 0.7)" };
    }
    if (highlightState.target === node.id) {
      return { fill: "#f59e0b", border: "#fde68a", glow: "rgba(245, 158, 11, 0.8)" };
    }
    switch (node.role) {
      case "hub":
        return { fill: "#8b5cf6", border: "#c4b5fd", glow: "rgba(139, 92, 246, 0.5)" };
      case "model":
        return { fill: "#f59e0b", border: "#fcd34d", glow: "rgba(245, 158, 11, 0.4)" };
      case "controller":
        return { fill: "#06b6d4", border: "#67e8f9", glow: "rgba(6, 182, 212, 0.5)" };
      case "utility":
        return { fill: "#10b981", border: "#6ee7b7", glow: "rgba(16, 185, 129, 0.5)" };
      default:
        return { fill: "#6366f1", border: "#a5b4fc", glow: "rgba(99, 102, 241, 0.4)" };
    }
  }

  // Camera Transformation (Pan & Zoom)
  let camera = { x: 0, y: 0, zoom: 1 };
  let isPanning = false;
  let panStart = { x: 0, y: 0 };
  let hoveredNode = null;
  let selectedNode = null;
  let draggedNode = null;
  let searchFilter = "";

  // Highlight State for Blast Radius
  const highlightState = {
    target: null,
    affectedSet: new Set(),
  };

  // Inspect existing impact report if embedded on page
  const impactDataTag = document.getElementById("impact-json-data");
  if (impactDataTag) {
    try {
      const imp = JSON.parse(impactDataTag.textContent);
      if (imp && imp.found) {
        highlightState.target = imp.module;
        imp.total_affected.forEach(m => highlightState.affectedSet.add(m));
      }
    } catch (_) {}
  }

  // Physics Step
  let simTicks = 0;
  const maxTicks = 320;

  function updatePhysics() {
    if (simTicks >= maxTicks && !draggedNode) return;
    simTicks++;

    const repulsion = 1400;
    const springLength = 110;
    const springStrength = 0.045;
    const damping = 0.84;
    const centerGravity = 0.012;

    // Repulsion between all nodes
    for (let i = 0; i < nodes.length; i++) {
      const a = nodes[i];
      for (let j = i + 1; j < nodes.length; j++) {
        const b = nodes[j];
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        let dist = Math.sqrt(dx * dx + dy * dy) || 1;
        if (dist < 350) {
          const force = repulsion / (dist * dist);
          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;
          if (!a.isDragging) { a.vx -= fx; a.vy -= fy; }
          if (!b.isDragging) { b.vx += fx; b.vy += fy; }
        }
      }

      // Center gravity
      const cdx = width / 2 - a.x;
      const cdy = height / 2 - a.y;
      if (!a.isDragging) {
        a.vx += cdx * centerGravity;
        a.vy += cdy * centerGravity;
      }
    }

    // Spring attraction along edges
    for (let e of edges) {
      const a = e.source;
      const b = e.target;
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const displacement = dist - springLength;
      const force = displacement * springStrength;
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;

      if (!a.isDragging) { a.vx += fx; a.vy += fy; }
      if (!b.isDragging) { b.vx -= fx; b.vy -= fy; }
    }

    // Apply velocities
    for (let n of nodes) {
      if (!n.isDragging) {
        n.vx *= damping;
        n.vy *= damping;
        n.x += n.vx;
        n.y += n.vy;
      }
    }
  }

  // Draw Function
  function draw() {
    ctx.save();
    ctx.clearRect(0, 0, width, height);

    // Apply Camera Transform
    ctx.translate(camera.x, camera.y);
    ctx.scale(camera.zoom, camera.zoom);

    // Connected set for hover / selection
    const activeFocusNode = hoveredNode || selectedNode;
    const connectedNodeIds = new Set();
    if (activeFocusNode) {
      connectedNodeIds.add(activeFocusNode.id);
      edges.forEach(e => {
        if (e.source.id === activeFocusNode.id) connectedNodeIds.add(e.target.id);
        if (e.target.id === activeFocusNode.id) connectedNodeIds.add(e.source.id);
      });
    }

    const hasHighlight = highlightState.target !== null || highlightState.affectedSet.size > 0;

    // Draw Edges
    edges.forEach(e => {
      const isConnected = activeFocusNode && (e.source.id === activeFocusNode.id || e.target.id === activeFocusNode.id);
      const isImpactEdge = highlightState.affectedSet.has(e.source.id) && (e.target.id === highlightState.target || highlightState.affectedSet.has(e.target.id));

      ctx.beginPath();
      ctx.moveTo(e.source.x, e.source.y);
      ctx.lineTo(e.target.x, e.target.y);

      if (isConnected) {
        ctx.strokeStyle = "#22d3ee";
        ctx.lineWidth = 2.4;
        ctx.shadowColor = "rgba(34, 211, 238, 0.6)";
        ctx.shadowBlur = 8;
      } else if (isImpactEdge) {
        ctx.strokeStyle = "#f43f5e";
        ctx.lineWidth = 2.2;
        ctx.shadowColor = "rgba(244, 63, 94, 0.7)";
        ctx.shadowBlur = 8;
      } else {
        const dim = (activeFocusNode || hasHighlight) ? 0.15 : 0.45;
        ctx.strokeStyle = `rgba(100, 116, 139, ${dim})`;
        ctx.lineWidth = 1.2;
        ctx.shadowBlur = 0;
      }
      ctx.stroke();
      ctx.shadowBlur = 0;

      // Draw directional arrow midway
      const mx = (e.source.x + e.target.x) / 2;
      const my = (e.source.y + e.target.y) / 2;
      const angle = Math.atan2(e.target.y - e.source.y, e.target.x - e.source.x);
      const arrowSize = 6;

      ctx.beginPath();
      ctx.moveTo(mx, my);
      ctx.lineTo(mx - arrowSize * Math.cos(angle - Math.PI / 6), my - arrowSize * Math.sin(angle - Math.PI / 6));
      ctx.lineTo(mx - arrowSize * Math.cos(angle + Math.PI / 6), my - arrowSize * Math.sin(angle + Math.PI / 6));
      ctx.closePath();
      ctx.fillStyle = isConnected ? "#22d3ee" : isImpactEdge ? "#f43f5e" : "rgba(100, 116, 139, 0.5)";
      ctx.fill();
    });

    // Draw Nodes
    nodes.forEach(n => {
      const isHovered = hoveredNode && hoveredNode.id === n.id;
      const isSelected = selectedNode && selectedNode.id === n.id;
      const isConnected = connectedNodeIds.has(n.id);
      const isAffected = highlightState.affectedSet.has(n.id);
      const isTarget = highlightState.target === n.id;
      const isMatchSearch = searchFilter && n.id.toLowerCase().includes(searchFilter.toLowerCase());

      const colors = getNodeColor(n);
      let alpha = 1;
      if (activeFocusNode && !isConnected && !isHovered && !isSelected) {
        alpha = 0.2;
      } else if (hasHighlight && !isAffected && !isTarget) {
        alpha = 0.25;
      }

      ctx.globalAlpha = alpha;

      // Pulse ring for target or search match
      if (isTarget || isMatchSearch) {
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.radius + 8 + Math.sin(Date.now() / 200) * 2, 0, Math.PI * 2);
        ctx.strokeStyle = isTarget ? "rgba(245, 158, 11, 0.8)" : "rgba(34, 211, 238, 0.8)";
        ctx.lineWidth = 2;
        ctx.stroke();
      }

      // Outer glow on hover or selected
      if (isHovered || isSelected || isAffected) {
        ctx.shadowColor = colors.glow;
        ctx.shadowBlur = 18;
      } else {
        ctx.shadowBlur = 0;
      }

      // Node Body Circle
      ctx.beginPath();
      ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
      ctx.fillStyle = colors.fill;
      ctx.fill();

      // Border
      ctx.lineWidth = isHovered || isSelected ? 3 : 1.5;
      ctx.strokeStyle = isHovered || isSelected ? "#ffffff" : colors.border;
      ctx.stroke();
      ctx.shadowBlur = 0;

      // Label
      ctx.font = isHovered || isSelected ? "bold 12px monospace" : "11px monospace";
      ctx.fillStyle = isHovered || isSelected ? "#ffffff" : "#cbd5e1";
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      ctx.fillText(n.label, n.x, n.y + n.radius + 5);

      ctx.globalAlpha = 1;
    });

    ctx.restore();
  }

  // Animation Loop
  function loop() {
    updatePhysics();
    draw();
    requestAnimationFrame(loop);
  }
  requestAnimationFrame(loop);

  // Screen to World coords
  function screenToWorld(sx, sy) {
    const rect = canvas.getBoundingClientRect();
    const x = (sx - rect.left - camera.x) / camera.zoom;
    const y = (sy - rect.top - camera.y) / camera.zoom;
    return { x, y };
  }

  function getNodeAt(x, y) {
    for (let i = nodes.length - 1; i >= 0; i--) {
      const n = nodes[i];
      const dx = n.x - x;
      const dy = n.y - y;
      if (dx * dx + dy * dy <= (n.radius + 4) * (n.radius + 4)) {
        return n;
      }
    }
    return null;
  }

  // Mouse Interaction Handlers
  canvas.addEventListener("mousedown", e => {
    const pt = screenToWorld(e.clientX, e.clientY);
    const hit = getNodeAt(pt.x, pt.y);
    if (hit) {
      draggedNode = hit;
      hit.isDragging = true;
      selectedNode = hit;
      showInspector(hit);
    } else {
      isPanning = true;
      panStart = { x: e.clientX - camera.x, y: e.clientY - camera.y };
    }
  });

  window.addEventListener("mousemove", e => {
    const pt = screenToWorld(e.clientX, e.clientY);
    if (draggedNode) {
      draggedNode.x = pt.x;
      draggedNode.y = pt.y;
      draggedNode.vx = 0;
      draggedNode.vy = 0;
      simTicks = 0; // wake physics
    } else if (isPanning) {
      camera.x = e.clientX - panStart.x;
      camera.y = e.clientY - panStart.y;
    } else {
      const hit = getNodeAt(pt.x, pt.y);
      if (hit !== hoveredNode) {
        hoveredNode = hit;
        canvas.style.cursor = hit ? "pointer" : "grab";
      }
    }
  });

  window.addEventListener("mouseup", () => {
    if (draggedNode) {
      draggedNode.isDragging = false;
      draggedNode = null;
    }
    isPanning = false;
  });

  // Wheel Zoom
  canvas.addEventListener("wheel", e => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.12 : 0.89;
    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    const newZoom = Math.max(0.3, Math.min(3.5, camera.zoom * zoomFactor));
    camera.x = mouseX - (mouseX - camera.x) * (newZoom / camera.zoom);
    camera.y = mouseY - (mouseY - camera.y) * (newZoom / camera.zoom);
    camera.zoom = newZoom;
  });

  // Inspector Drawer Handler
  const inspector = document.getElementById("graph-inspector");
  function showInspector(n) {
    if (!inspector) return;
    inspector.style.display = "block";
    const titleEl = document.getElementById("ins-title");
    const pathEl = document.getElementById("ins-path");
    const linesEl = document.getElementById("ins-lines");
    const funcsEl = document.getElementById("ins-funcs");
    const classesEl = document.getElementById("ins-classes");
    const inDegEl = document.getElementById("ins-indeg");
    const outDegEl = document.getElementById("ins-outdeg");
    const instabEl = document.getElementById("ins-instab");
    const traceBtn = document.getElementById("ins-trace-btn");

    if (titleEl) titleEl.textContent = n.id;
    if (pathEl) pathEl.textContent = n.path;
    if (linesEl) linesEl.textContent = n.lines;
    if (funcsEl) funcsEl.textContent = n.functions_count;
    if (classesEl) classesEl.textContent = n.classes_count;
    if (inDegEl) inDegEl.textContent = n.in_degree;
    if (outDegEl) outDegEl.textContent = n.out_degree;
    if (instabEl) instabEl.textContent = n.instability;

    if (traceBtn) {
      traceBtn.onclick = () => {
        const input = document.getElementById("target");
        if (input) {
          input.value = n.id;
          input.scrollIntoView({ behavior: "smooth", block: "center" });
          input.focus();
        }
      };
    }
  }

  const closeBtn = document.getElementById("ins-close");
  if (closeBtn) {
    closeBtn.addEventListener("click", () => {
      if (inspector) inspector.style.display = "none";
      selectedNode = null;
    });
  }

  // Zoom Toolbar Controls
  const btnZoomIn = document.getElementById("ctrl-zoom-in");
  const btnZoomOut = document.getElementById("ctrl-zoom-out");
  const btnReset = document.getElementById("ctrl-reset");
  const btnFullscreen = document.getElementById("ctrl-fullscreen");

  if (btnZoomIn) {
    btnZoomIn.onclick = () => {
      camera.zoom = Math.min(3.5, camera.zoom * 1.25);
    };
  }
  if (btnZoomOut) {
    btnZoomOut.onclick = () => {
      camera.zoom = Math.max(0.3, camera.zoom * 0.8);
    };
  }
  if (btnReset) {
    btnReset.onclick = () => {
      camera = { x: 0, y: 0, zoom: 1 };
      simTicks = 0;
    };
  }
  if (btnFullscreen) {
    btnFullscreen.onclick = () => {
      if (!document.fullscreenElement) {
        container.parentElement.requestFullscreen().catch(() => {});
      } else {
        document.exitFullscreen().catch(() => {});
      }
    };
  }

  // Search input inside graph
  const searchInput = document.getElementById("graph-search");
  if (searchInput) {
    searchInput.addEventListener("input", e => {
      searchFilter = e.target.value.trim();
      if (searchFilter) {
        const found = nodes.find(n => n.id.toLowerCase().includes(searchFilter.toLowerCase()));
        if (found) {
          camera.x = width / 2 - found.x * camera.zoom;
          camera.y = height / 2 - found.y * camera.zoom;
          selectedNode = found;
          showInspector(found);
        }
      }
    });
  }
})();
