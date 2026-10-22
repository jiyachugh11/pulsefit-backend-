'use strict';

const $ = (selector) => document.querySelector(selector);
const encode = encodeURIComponent;
const recordConfig = {
  users: {id: 'user_id', singular: 'user', columns: ['user_id', 'first_name', 'last_name', 'email', 'joined_at']},
  devices: {id: 'device_id', singular: 'device', columns: ['device_id', 'user_id', 'device_type', 'brand', 'model', 'registered_at']},
  challenges: {id: 'challenge_id', singular: 'challenge', columns: ['challenge_id', 'challenge_name', 'start_date', 'end_date']}
};

function notify(message, error = false) {
  const notice = $('#notice');
  notice.textContent = message;
  notice.className = error ? 'error' : '';
  notice.hidden = false;
}

async function api(path, method = 'GET', body) {
  let response;
  try {
    response = await fetch(path, {method, headers: {'Content-Type': 'application/json'},
      ...(body === undefined ? {} : {body: JSON.stringify(body)})});
  } catch {
    throw new Error('Cannot reach PulseFit. Check that the FastAPI server is running.');
  }
  const data = await response.json();
  if (!response.ok) {
    const detail = Array.isArray(data.detail)
      ? data.detail.map((item) => `${item.loc.join('.')}: ${item.msg}`).join('; ')
      : data.detail || `Request failed (${response.status}).`;
    throw new Error(detail);
  }
  return data;
}

function showTableMessage(target, message, error = false) {
  const p = document.createElement('p');
  p.className = `empty${error ? ' error-state' : ''}`;
  p.textContent = message;
  $(target).replaceChildren(p);
}

// Render database values using textContent, never HTML interpolation.
function table(target, rows, columns, actions = []) {
  if (!rows.length) {
    showTableMessage(target, 'No records found. Add a record or run the sample setup.');
    return;
  }
  const element = document.createElement('table');
  const head = element.createTHead().insertRow();
  for (const column of [...columns, ...(actions.length ? ['actions'] : [])]) {
    const th = document.createElement('th');
    th.scope = 'col';
    th.textContent = column.replaceAll('_', ' ');
    head.append(th);
  }
  const body = element.createTBody();
  for (const row of rows) {
    const tr = body.insertRow();
    for (const column of columns) {
      const value = row[column];
      tr.insertCell().textContent = value == null ? '—' : String(value);
    }
    if (actions.length) {
      const td = tr.insertCell();
      for (const action of actions) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = action.label === 'Delete' ? 'danger' : 'secondary';
        button.textContent = action.label;
        button.addEventListener('click', () => run(button, () => action.handler(row)));
        td.append(button);
      }
    }
  }
  $(target).replaceChildren(element);
}

async function run(button, task) {
  if (button) button.disabled = true;
  try { await task(); }
  catch (error) { notify(error.message, true); }
  finally { if (button) button.disabled = false; }
}

function bindForm(selector, task) {
  $(selector).addEventListener('submit', (event) => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.currentTarget));
    const action = event.submitter?.value;
    run(event.submitter, () => task(data, action));
  });
}

function resetEditor(resource) {
  const config = recordConfig[resource];
  const form = $(`#${resource}-form`);
  form.reset();
  delete form.dataset.editId;
  form.elements[config.id].readOnly = false;
  form.querySelector('.primary').textContent = `Add ${config.singular}`;
  form.querySelector('.cancel-edit').hidden = true;
  $(`#${resource}-form-title`).textContent = `Add ${config.singular}`;
}

function editRecord(resource, row) {
  const config = recordConfig[resource];
  const form = $(`#${resource}-form`);
  for (const input of form.querySelectorAll('input')) input.value = row[input.name] ?? '';
  form.dataset.editId = row[config.id];
  form.elements[config.id].readOnly = true;
  form.querySelector('.primary').textContent = 'Save changes';
  form.querySelector('.cancel-edit').hidden = false;
  $(`#${resource}-form-title`).textContent = `Edit ${config.singular}`;
  form.querySelector('input:not([readonly])').focus();
}

async function loadRecords(resource) {
  const config = recordConfig[resource];
  try {
    const rows = await api(`/${resource}`);
    $(`#${resource}-count`).textContent = rows.length;
    table(`#${resource}-table`, rows, config.columns, [
      {label: 'Edit', handler: (row) => editRecord(resource, row)},
      {label: 'Delete', handler: async (row) => {
        if (!confirm(`Delete ${row[config.id]} from ${resource}? Related data in other stores is not automatically deleted.`)) return;
        await api(`/${resource}/${encode(row[config.id])}`, 'DELETE');
        if ($(`#${resource}-form`).dataset.editId === row[config.id]) resetEditor(resource);
        notify('Record deleted.');
        await loadRecords(resource);
      }}
    ]);
  } catch (error) {
    $(`#${resource}-count`).textContent = '—';
    showTableMessage(`#${resource}-table`, error.message, true);
    throw error;
  }
}

for (const [resource, config] of Object.entries(recordConfig)) {
  bindForm(`#${resource}-form`, async (data) => {
    const editId = $(`#${resource}-form`).dataset.editId;
    if (editId) delete data[config.id];
    await api(`/${resource}${editId ? '/' + encode(editId) : ''}`, editId ? 'PUT' : 'POST', data);
    resetEditor(resource);
    notify(editId ? 'Changes saved.' : `${config.singular[0].toUpperCase() + config.singular.slice(1)} created.`);
    await loadRecords(resource);
  });
  $(`#${resource}-form .cancel-edit`).addEventListener('click', () => resetEditor(resource));
}

document.querySelectorAll('.refresh').forEach((button) => button.addEventListener('click', () =>
  run(button, () => loadRecords(button.dataset.resource))));

document.querySelectorAll('[data-tab]').forEach((button) => button.addEventListener('click', () => {
  const tab = button.dataset.tab;
  document.querySelectorAll('.panel').forEach((panel) => panel.hidden = panel.id !== tab);
  document.querySelectorAll('[data-tab]').forEach((item) => {
    item.classList.toggle('active', item === button);
    item.setAttribute('aria-current', item === button ? 'page' : 'false');
  });
  $('#breadcrumb').textContent = button.textContent.trim().replace(/^\d+/, '').trim();
  $('#notice').hidden = true;
  if (recordConfig[tab]) run(null, () => loadRecords(tab));
}));

bindForm('#metadata-find', async ({device_id}) => {
  const doc = await api(`/metadata/${encode(device_id)}`);
  $('#metadata-json').value = JSON.stringify(doc, null, 2);
  notify('Metadata loaded.');
});
bindForm('#metadata-form', async (_, method) => {
  let doc;
  try { doc = JSON.parse($('#metadata-json').value); }
  catch { throw new Error('Enter valid JSON in the metadata editor.'); }
  if (!doc || typeof doc.device_id !== 'string' || !doc.device_id.trim()) throw new Error('Include a device_id in the document.');
  if (method === 'DELETE' && !confirm(`Delete metadata for ${doc.device_id}?`)) return;
  const result = await api(`/metadata${method === 'POST' ? '' : '/' + encode(doc.device_id)}`,
    method, method === 'DELETE' ? undefined : doc);
  if (method !== 'DELETE') $('#metadata-json').value = JSON.stringify(result, null, 2);
  notify(method === 'DELETE' ? 'Metadata deleted.' : 'Metadata saved.');
});

async function loadTelemetry(data) {
  try {
    const rows = await api(`/telemetry/${encode(data.device_id)}?reading_date=${encode(data.reading_date)}`);
    table('#telemetry-table', rows, ['reading_ts', 'heart_rate', 'steps', 'spo2', 'latitude', 'longitude'], [
      {label: 'Delete', handler: async (row) => {
        if (!confirm(`Delete reading at ${row.reading_ts}?`)) return;
        await api(`/telemetry/${encode(row.device_id)}/${encode(row.reading_date)}/${encode(row.reading_ts)}`, 'DELETE');
        notify('Reading deleted.');
        await loadTelemetry(data);
      }}
    ]);
  } catch (error) { showTableMessage('#telemetry-table', error.message, true); throw error; }
}
bindForm('#telemetry-find', loadTelemetry);
bindForm('#telemetry-form', async (data) => {
  data.reading_ts = new Date(data.reading_ts + 'Z').toISOString();
  data.reading_date = data.reading_ts.slice(0, 10);
  for (const field of ['heart_rate', 'steps', 'spo2', 'latitude', 'longitude']) data[field] = Number(data[field]);
  await api('/telemetry', 'POST', data);
  $('#telemetry-find').elements.device_id.value = data.device_id;
  $('#telemetry-find').elements.reading_date.value = data.reading_date;
  notify('Reading saved.');
  await loadTelemetry(data);
});

async function loadSocial(user_id) {
  // AllSettled permits one independent query to report its result if the other fails.
  const results = await Promise.allSettled(['following', 'recommendations'].map(async (kind) => {
    try {
      const rows = await api(`/social/${encode(user_id)}/${kind}`);
      table(`#${kind}-table`, rows, ['user_id', 'name', ...(kind === 'recommendations' ? ['shared_connections'] : [])]);
    } catch (error) { showTableMessage(`#${kind}-table`, error.message, true); throw error; }
  }));
  const failure = results.find((result) => result.status === 'rejected');
  if (failure) throw failure.reason;
}
bindForm('#social-find', ({user_id}) => loadSocial(user_id));
bindForm('#social-form', async (data, method) => {
  await api('/social/follow', method, data);
  $('#social-find').elements.user_id.value = data.user_id;
  notify(method === 'POST' ? 'Follow relationship saved.' : 'Follow relationship removed.');
  await loadSocial(data.user_id);
});

async function loadLeaderboard({day}) {
  try {
    table('#leaderboard-table', await api(`/leaderboard?day=${encode(day)}`), ['rank', 'user_id', 'steps']);
  } catch (error) { showTableMessage('#leaderboard-table', error.message, true); throw error; }
}
bindForm('#leaderboard-find', loadLeaderboard);
bindForm('#leaderboard-form', async ({user_id, steps, day}) => {
  await api(`/leaderboard/${encode(user_id)}?day=${encode(day)}`, 'PUT', {steps: Number(steps)});
  $('#leaderboard-find').elements.day.value = day;
  notify('Daily score updated.');
  await loadLeaderboard({day});
});

run(null, () => loadRecords('users'));
