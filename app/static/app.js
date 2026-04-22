/* ── Wizard ─────────────────────────────────────────────────────────── */
function wizardNext(step) {
  const panel = document.querySelector(`.wizard-panel[data-step="${step}"]`);
  if (!panel) return;

  const required = panel.querySelectorAll('[required]');
  let valid = true;
  required.forEach(el => {
    if (!el.value.trim()) { el.classList.add('error'); valid = false; }
    else el.classList.remove('error');
  });
  if (!valid) return;

  document.querySelectorAll('.wizard-step').forEach(s => s.classList.remove('active'));
  const nextStep = document.querySelector(`.wizard-step[data-step="${step + 1}"]`);
  if (nextStep) nextStep.classList.add('active');

  document.querySelectorAll('.wizard-panel').forEach(p => p.classList.add('hidden'));
  const nextPanel = document.querySelector(`.wizard-panel[data-step="${step + 1}"]`);
  if (nextPanel) nextPanel.classList.remove('hidden');
}

function wizardSubmitting(form) {
  const btn = form.querySelector('[type="submit"]');
  if (btn) {
    btn.disabled = true;
    btn.textContent = 'Working…';
  }
}

async function wizardCloneAndAdvance(btn) {
  const repoSelect = document.getElementById('repo_select');
  const githubUrlEl = document.getElementById('github_url');
  const githubTokenEl = document.getElementById('github_token');
  const githubUrl = githubUrlEl ? githubUrlEl.value.trim() : '';
  const githubToken = githubTokenEl ? githubTokenEl.value.trim() : '';

  if (!githubUrl && !(repoSelect && repoSelect.value)) {
    alert('Please enter a GitHub URL or select an existing repo');
    return;
  }

  // Existing repo selected, no new URL — just advance
  if (!githubUrl && repoSelect && repoSelect.value) {
    wizardNext(1);
    return;
  }

  const origText = btn.textContent;
  btn.disabled = true;
  btn.textContent = 'Cloning…';

  try {
    const fd = new FormData();
    fd.append('github_url', githubUrl);
    fd.append('github_token', githubToken);

    const res = await fetch('/api/wizard/clone', { method: 'POST', body: fd });
    const html = await res.text();

    const tmp = document.createElement('div');
    tmp.innerHTML = html;

    // Check for error option
    const errOpt = tmp.querySelector('option[disabled]');
    if (errOpt) { alert(errOpt.textContent); return; }

    // Update repo select with returned repo_id
    const hiddenEl = tmp.querySelector('input[name="repo_id"]');
    if (hiddenEl && repoSelect) {
      const repoId = hiddenEl.value;
      if (!repoSelect.querySelector(`option[value="${repoId}"]`)) {
        const opt = document.createElement('option');
        opt.value = repoId;
        opt.textContent = githubUrl.split('/').pop().replace('.git', '');
        repoSelect.appendChild(opt);
      }
      repoSelect.value = repoId;
    }

    // Populate entrypoint select
    const entrySelect = document.getElementById('entrypoint');
    if (entrySelect) {
      entrySelect.innerHTML = '<option value="">— Select a script —</option>';
      tmp.querySelectorAll('option').forEach(opt => entrySelect.appendChild(opt.cloneNode(true)));
    }

    wizardNext(1);
  } catch (e) {
    alert('Clone failed: ' + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = origText;
  }
}

/* ── Cron helper ───────────────────────────────────────────────────── */
function initCronHelper() {
  // Run validation immediately if cron expression already has a value
  const input = document.getElementById('cron_expression');
  if (input && input.value.trim()) {
    validateCronNow();
  }
}

function applyCronPreset(value) {
  const input = document.getElementById('cron_expression');
  if (!input) return;
  input.value = value;
  validateCronNow();
}

async function validateCronNow() {
  const input = document.getElementById('cron_expression');
  if (!input) return;
  const feedback = document.getElementById('cron_feedback');
  const nextRunBlock = document.getElementById('cron_next_run_block');
  const nextRunEl = document.getElementById('cron_next_run');
  if (!feedback) return;

  const expr = input.value.trim();
  if (!expr) {
    feedback.textContent = '';
    feedback.className = 'cron-feedback';
    if (nextRunBlock) nextRunBlock.style.display = 'none';
    return;
  }

  // Show "Checking..." state
  feedback.textContent = 'Checking…';
  feedback.className = 'cron-feedback checking';

  try {
    const encoded = encodeURIComponent(expr);
    const res = await fetch(`/api/validate/cron?expression=${encoded}`);
    const data = await res.json();

    if (data.valid) {
      feedback.textContent = 'Valid cron expression';
      feedback.className = 'cron-feedback valid';
      // Fetch next run preview
      fetchNextRun(expr);
    } else {
      feedback.textContent = data.error || 'Invalid cron expression';
      feedback.className = 'cron-feedback invalid';
      if (nextRunBlock) nextRunBlock.style.display = 'none';
    }
  } catch (e) {
    feedback.textContent = 'Could not validate expression';
    feedback.className = 'cron-feedback invalid';
  }
}

async function fetchNextRun(expr) {
  const nextRunBlock = document.getElementById('cron_next_run_block');
  const nextRunEl = document.getElementById('cron_next_run');
  if (!nextRunBlock || !nextRunEl) return;

  try {
    const encoded = encodeURIComponent(expr);
    const res = await fetch(`/api/validate/cron/nextrun?expression=${encoded}`);
    const data = await res.json();
    if (data.nextrun) {
      const dt = new Date(data.nextrun);
      nextRunEl.textContent = dt.toLocaleString();
      nextRunBlock.style.display = 'block';
    } else {
      nextRunEl.textContent = 'Could not determine next run';
      nextRunBlock.style.display = 'block';
    }
  } catch (e) {
    nextRunBlock.style.display = 'none';
  }
}

/* ── Help panel toggle ───────────────────────────────────────────────── */
function toggleHelp(id) {
  const panel = document.getElementById(id);
  if (!panel) return;
  panel.style.display = panel.style.display === 'block' ? 'none' : 'block';
}

/* ── Log tail (SSE) ─────────────────────────────────────────────────── */
let logSource = null;
function startLogTail(jobId) {
  stopLogTail();
  const container = document.getElementById('log_container');
  if (!container) return;
  logSource = new EventSource(`/api/jobs/${jobId}/logs/stream`);
  logSource.onmessage = (e) => {
    const line = document.createElement('div');
    line.className = 'log-line';
    line.textContent = e.data;
    container.appendChild(line);
    container.scrollTop = container.scrollHeight;
  };
  logSource.onerror = () => stopLogTail();
}
function stopLogTail() {
  if (logSource) { logSource.close(); logSource = null; }
}

/* ── Env vars editor ────────────────────────────────────────────────── */
function addEnvRow() {
  const table = document.getElementById('env_table');
  if (!table) return;
  const row = document.createElement('tr');
  row.innerHTML = `
    <td><input type="text" name="env_key" placeholder="KEY" /></td>
    <td><input type="text" name="env_value" placeholder="value" /></td>
    <td class="env-del-col"><button type="button" class="env-del-btn" onclick="this.closest('tr').remove()">✕</button></td>
  `;
  table.appendChild(row);
}
