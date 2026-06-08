
            const templatesList = JSON.parse(document.getElementById('templatesLive').textContent || '[]');

            async function syncTemplates() {
                const btn = document.getElementById('syncBtn');
                const originalHtml = btn.innerHTML;
                btn.disabled = true;
                btn.innerHTML = `<span class="animate-spin rounded-full h-4 w-4 border-b-2 border-slate-600"></span> Syncing...`;

                try {
                    const res = await fetch('/api/templates/sync', { method: 'POST' });
                    const data = await res.json();
                    if (res.ok) {
                        showToast(`Successfully synced ${data.count || 0} templates!`, 'success');
                        setTimeout(() => location.reload(), 1500);
                    } else {
                        showToast(data.error || 'Sync failed', 'error');
                    }
                } catch (err) {
                    showToast('Network error during sync', 'error');
                } finally {
                    btn.disabled = false;
                    btn.innerHTML = originalHtml;
                }
            }
            const templateData = templatesList.reduce((acc, t) => { acc[t.name] = t.content; return acc; }, {});
            const templateComponents = templatesList.reduce((acc, t) => { acc[t.name] = t.components; return acc; }, {});

            // Profile Menu Toggle
            function toggleProfileMenu(event) {
                event.stopPropagation();
                const menu = document.getElementById('profileMenu');
                menu.classList.toggle('hidden');

                // Add a one-time listener to close when clicking outside
                if (!menu.classList.contains('hidden')) {
                    const closeMenu = (e) => {
                        if (!menu.contains(e.target)) {
                            menu.classList.add('hidden');
                            document.removeEventListener('click', closeMenu);
                        }
                    };
                    setTimeout(() => document.addEventListener('click', closeMenu), 0);
                }
            }

            // Timestamp Formatting Helper
            function formatDateTime(ts) {
                if (!ts) return "";
                try {
                    let cleanTs = ts.toString().replace(' ', 'T');
                    if (!cleanTs.includes('Z') && !cleanTs.includes('+') && !cleanTs.match(/-\d{2}:?\d{2}$/)) {
                        cleanTs += 'Z';
                    }
                    let d = new Date(cleanTs);
                    if (isNaN(d.getTime())) return ts;

                    // Clamp future times (caused by server clock skew) to current browser "now"
                    const browserNow = new Date();
                    if (d > browserNow) d = browserNow;

                    const options = {
                        day: '2-digit',
                        month: 'short',
                        hour: 'numeric',
                        minute: '2-digit',
                        hour12: true,
                        timeZone: 'Asia/Kolkata'
                    };
                    return d.toLocaleString('en-IN', options).toUpperCase();
                } catch (e) { return ts; }
            }

            function formatTimeOnly(ts) {
                if (!ts) return "";
                try {
                    if (ts.length <= 8 && ts.includes(':') && !ts.includes('-')) return ts;
                    let cleanTs = ts.toString().replace(' ', 'T');
                    if (!cleanTs.includes('Z') && !cleanTs.includes('+') && !cleanTs.match(/-\d{2}:?\d{2}$/)) {
                        cleanTs += 'Z';
                    }
                    let d = new Date(cleanTs);
                    if (isNaN(d.getTime())) return ts;

                    // Clamp future times
                    const browserNow = new Date();
                    if (d > browserNow) d = browserNow;

                    return d.toLocaleTimeString('en-IN', {
                        hour: 'numeric',
                        minute: '2-digit',
                        hour12: true,
                        timeZone: 'Asia/Kolkata'
                    }).toUpperCase();
                } catch (e) { return ts; }
            }

            function formatAllSyncTimes() {
                const elements = document.querySelectorAll('.sync-time');
                elements.forEach(el => {
                    const val = (el.textContent || el.innerText || "").trim();
                    // If it looks like a raw SQLite timestamp (YYYY-MM-DD HH:MM:SS)
                    if (val && val.includes('-') && val.includes(':') && !val.includes(',')) {
                        const formatted = formatDateTime(val);
                        if (formatted !== val) el.innerText = formatted;
                    }
                });
            }

            // Run on load and whenever tabs switch
            document.addEventListener('DOMContentLoaded', formatAllSyncTimes);
            window.addEventListener('load', formatAllSyncTimes);
            setInterval(formatAllSyncTimes, 2000);

            function openTemplatePreview(name) {
                const content = templateData[name] || '';
                const components = templateComponents[name] || [];
                openPreviewModal({ content, components, isTemplateTab: true });
            }

            // Custom Toast System
            function showToast(message, type = 'info') {
                const container = document.getElementById('toastContainer');
                const toast = document.createElement('div');
                const bgColor = type === 'success' ? 'bg-emerald-600' : (type === 'error' ? 'bg-rose-600' : 'bg-slate-800');

                toast.className = `toast ${bgColor} text-white px-6 py-4 rounded-2xl shadow-2xl flex items-center gap-3 min-w-[300px] border border-white/10 glass`;
                toast.innerHTML = `
                <div class="flex-grow font-medium text-sm">${message}</div>
                <button onclick="this.parentElement.remove()" class="text-white/50 hover:text-white transition-colors">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                </button>
            `;
                container.appendChild(toast);
                setTimeout(() => toast.remove(), 5000);
            }

            // Tab Switching
            function switchTab(tab) {
                document.querySelectorAll('.tab-btn').forEach(b => {
                    b.classList.remove('active', 'text-green-600', 'border-green-600', 'border-b-2');
                    b.classList.add('text-slate-500');
                });
                document.getElementById('tab-' + tab).classList.add('active', 'text-green-600', 'border-green-600', 'border-b-2');
                document.getElementById('tab-' + tab).classList.remove('text-slate-500');

                const contentId = 'content-' + tab;
                const content = document.getElementById(contentId);
                if (content) {
                    document.querySelectorAll('main > div').forEach(div => div.classList.add('hidden'));
                    content.classList.remove('hidden');
                }

                if (tab === 'templates') {
                    content.classList.add('block');
                } else if (tab === 'history') {
                    content.classList.add('block');
                    loadHistory();
                } else if (tab === 'chat') {
                    content.classList.remove('hidden');
                    content.classList.add('flex');
                    loadChatContacts();
                } else {
                    content.classList.add('grid');
                }
            }

            // History Management
            async function loadHistory() {
                const tbody = document.getElementById('historyTableBody');
                tbody.innerHTML = `<tr><td colspan="6" class="px-8 py-12 text-center text-sm text-slate-500 italic">Loading history...</td></tr>`;

                try {
                    const response = await fetch('/api/history');
                    const campaigns = await response.json();

                    if (campaigns.length === 0) {
                        tbody.innerHTML = `<tr><td colspan="6" class="px-8 py-12 text-center text-sm text-slate-500 italic">No campaigns found.</td></tr>`;
                        return;
                    }

                    tbody.innerHTML = campaigns.map(c => `
                    <tr class="hover:bg-slate-50/80 transition-colors">
                        <td class="px-8 py-5 text-sm font-bold text-slate-800">${c.name}</td>
                        <td class="px-8 py-5 text-xs text-slate-500 capitalize sync-time">${c.timestamp}</td>
                        <td class="px-8 py-5 text-center text-sm font-medium text-slate-600">${c.sent_success}</td>
                        <td class="px-8 py-5 text-center text-sm font-medium text-rose-600">${c.failed || 0}</td>
                        <td class="px-8 py-5 text-center text-sm font-medium text-blue-600">${c.delivered || 0}</td>
                        <td class="px-8 py-5 text-center text-sm font-medium text-emerald-600">${c.read || 0}</td>
                        <td class="px-8 py-5 text-right">
                            <button onclick="viewCampaignDetails(${c.id}, '${(c.name || 'Campaign').replace(/'/g, "\\'")}', '${c.timestamp}')" class="text-indigo-600 hover:text-indigo-800 text-xs font-bold flex items-center gap-1 justify-end">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path></svg>
                                Details
                            </button>
                        </td>
                    </tr>
                `).join('');
                    formatAllSyncTimes();
                } catch (err) {
                    tbody.innerHTML = `<tr><td colspan="6" class="px-8 py-12 text-center text-rose-500 italic text-sm">Failed to load history.</td></tr>`;
                }
            }

            window.currentHistoryCampaignId = null;
            async function viewCampaignDetails(id, name, date) {
                currentHistoryCampaignId = id;
                const modal = document.getElementById('historyDetailModal');
                document.getElementById('detailCampaignName').innerText = name;
                document.getElementById('detailCampaignDate').innerText = formatDateTime(date);

                // Show loading stats
                document.getElementById('statSent').innerText = "...";
                document.getElementById('statDelivered').innerText = "...";
                document.getElementById('statRead').innerText = "...";
                document.getElementById('statFailed').innerText = "...";
                document.getElementById('detailTableBody').innerHTML = `<tr><td colspan="4" class="px-6 py-12 text-center text-slate-400">Loading details...</td></tr>`;

                modal.classList.remove('hidden');
                modal.classList.add('flex');

                try {
                    const response = await fetch(`/api/campaign/${id}/details`);
                    const data = await response.json();

                    // Update stats
                    document.getElementById('statSent').innerText = data.stats.sent;
                    document.getElementById('statDelivered').innerText = data.stats.delivered;
                    document.getElementById('statRead').innerText = data.stats.read;
                    document.getElementById('statFailed').innerText = data.stats.failed;

                    // Update table
                    const tbody = document.getElementById('detailTableBody');
                    if (data.messages.length === 0) {
                        tbody.innerHTML = `<tr><td colspan="4" class="px-6 py-12 text-center text-slate-400">No messages found for this campaign.</td></tr>`;
                    } else {
                        tbody.innerHTML = data.messages.map(m => {
                            let statusColor = 'text-slate-600 bg-slate-100';
                            if (m.status === 'delivered') statusColor = 'text-blue-700 bg-blue-100';
                            if (m.status === 'read') statusColor = 'text-emerald-700 bg-emerald-100';
                            if (m.status === 'failed') statusColor = 'text-rose-700 bg-rose-100';

                            return `
                            <tr class="hover:bg-slate-50 transition-colors">
                                <td class="px-6 py-4 font-medium text-slate-800">${m.phone}</td>
                                <td class="px-6 py-4">
                                    <span class="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${statusColor}">
                                        ${m.status}
                                    </span>
                                </td>
                                <td class="px-6 py-4 text-xs text-slate-400 sync-time">${m.timestamp}</td>
                                <td class="px-6 py-4 text-xs ${m.status === 'failed' ? 'text-rose-500 font-medium' : 'text-slate-400'}">
                                    ${m.error_message || (m.status === 'sent' ? 'Sent but not delivered' : '')}
                                </td>
                            </tr>
                        `;
                        }).join('');
                        formatAllSyncTimes();
                    }
                } catch (err) {
                    showToast('Failed to load campaign details', 'error');
                }
            }

            function closeHistoryModal() {
                const modal = document.getElementById('historyDetailModal');
                modal.classList.add('hidden');
                modal.classList.remove('flex');
            }

            // --- Rest of original logic with showToast replaces ---

            const fileInput = document.getElementById('fileInput');
            const fileName = document.getElementById('fileName');
            const campaignForm = document.getElementById('campaignForm');
            const submitBtn = document.getElementById('submitBtn');

            document.getElementById('dropzone').onclick = () => fileInput.click();
            let currentFileColumns = [];
            let currentTemplateVars = [];
            let currentHeaderType = "NONE";
            let selectedTemplateLang = "en_US";

            function toggleDeliveryMethod(method) {
                const bulkArea = document.getElementById('bulkDeliveryArea');
                const singleArea = document.getElementById('singleDeliveryArea');

                if (method === 'bulk') {
                    bulkArea.classList.remove('hidden');
                    singleArea.classList.add('hidden');
                } else {
                    bulkArea.classList.add('hidden');
                    singleArea.classList.remove('hidden');
                }

                // Re-render templates mappings if a template is selected
                if (document.getElementById('templateName').value) {
                    const template = templatesList.find(t => t.name === document.getElementById('templateName').value);
                    if (template) {
                        renderMappingUI(template.variable_map || {});
                    }
                }
            }

            fileInput.onchange = async () => {
                if (fileInput.files.length > 0) {
                    const file = fileInput.files[0];
                    fileName.innerText = file.name;
                    document.getElementById('dropzone').classList.add('bg-green-50', 'border-green-500');

                    // Get Columns from Backend
                    const formData = new FormData();
                    formData.append('file', file);
                    try {
                        const res = await fetch('/api/get-columns', { method: 'POST', body: formData });
                        const data = await res.json();
                        if (res.ok) {
                            currentFileColumns = data.columns;
                            document.getElementById('mappingStatus').innerText = `${currentFileColumns.length} columns found`;
                            renderMappingUI();
                        }
                    } catch (e) { console.error('Error fetching columns', e); }
                }
            };

            function handleTemplateChange(select) {
                const templateName = select.value;
                if (!templateName) {
                    document.getElementById('mappingArea').classList.add('hidden');
                    return;
                }

                const template = templatesList.find(t => t.name === templateName);
                if (!template) return;

                // USE full_content if available (includes Header/Body/Footer) to detect ALL variables {{n}}
                const content = template.full_content || template.content || "";
                const components = template.components || [];
                const varMap = template.variable_map || {};

                // Extract Variables {{n}}
                const matches = content.match(/\x7b\x7b\d+\x7d\x7d/g) || [];
                currentTemplateVars = [...new Set(matches.map(m => m.replace(/[\x7b\x7d]/g, "")))].sort((a, b) => a - b);

                // Check for Media Header
                const header = components.find(c => c.type === 'HEADER');
                currentHeaderType = header ? header.format : "NONE";
                
                // Smart Auto-Fill: Priority 1: dedicated media_url column, Priority 2: components meta, Priority 3: localStorage
                currentHeaderSampleUrl = template.media_url || "";
                if (!currentHeaderSampleUrl) {
                    currentHeaderSampleUrl = (header && header.example) ? (header.example._original_url || "") : "";
                }
                if (!currentHeaderSampleUrl && currentHeaderType !== 'NONE' && currentHeaderType !== 'TEXT') {
                    currentHeaderSampleUrl = localStorage.getItem(`last_header_url_${templateName}`) || "";
                }
                
                selectedTemplateLang = template.language || "en_US";

                document.getElementById('mappingArea').classList.remove('hidden');
                renderMappingUI(varMap);
            }

            function renderMappingUI(variableMap = {}) {
                const list = document.getElementById('mappingList');
                const method = document.querySelector('input[name="delivery_method"]:checked')?.value || 'bulk';

                if (method === 'bulk' && !currentFileColumns.length) {
                    list.innerHTML = `<p class="text-[10px] text-amber-600 bg-amber-50 p-2 rounded">Please upload a file first to map variables.</p>`;
                    return;
                }

                let html = "";

                // Media Header Mapping
                if (['IMAGE', 'VIDEO', 'DOCUMENT'].includes(currentHeaderType)) {
                    if (method === 'bulk') {
                        html += `
                        <div class="space-y-2 p-3 bg-slate-50 rounded-xl border border-slate-200">
                            <div class="flex items-center gap-3">
                                <span class="text-[10px] font-bold text-slate-500 w-24">Header (${currentHeaderType})</span>
                                <select name="map_header" id="bulk_header_map" class="flex-1 bg-white border border-slate-200 rounded-lg outline-none text-[10px] font-medium p-1" onchange="document.querySelector('input[name=\\'val_header\\']').disabled = (this.value !== '')">
                                    <option value="">-- Use Fixed URL below --</option>
                                    <option value="__UPLOADED__">-- Use Uploaded Campaign Media --</option>
                                    ${currentFileColumns.map(c => `<option value="${c}">Use Column: ${c}</option>`).join('')}
                                </select>
                            </div>
                            <div class="flex items-center gap-3">
                                <span class="text-[10px] font-bold text-slate-400 w-24 ml-1">Fixed URL</span>
                                <input type="text" name="val_header" value="${currentHeaderSampleUrl}" class="flex-1 bg-white border border-slate-200 rounded-lg outline-none text-[10px] font-medium p-1 disabled:opacity-50" placeholder="Paste image link here...">
                            </div>
                            <p class="text-[9px] text-slate-400 italic ml-24">Select "Use Uploaded Campaign Media" to use the file you uploaded above, map a column, or paste a link.</p>
                        </div>
                    `;
                    } else {
                        html += `
                        <div class="flex items-center gap-3 p-2 bg-white rounded-lg border border-slate-200">
                            <span class="text-[10px] font-bold text-slate-500 w-24">Header URL</span>
                            <input type="text" name="val_header" value="${currentHeaderSampleUrl}" class="flex-1 bg-transparent border-none outline-none text-[10px] font-medium" placeholder="https://example.com/image.jpg">
                        </div>
                    `;
                    }
                }

                // Body Variables Mapping
                currentTemplateVars.forEach(v => {
                    const mapKey = v.toString();
                    // Use variableMap if available
                    const label = (variableMap && variableMap[mapKey])
                        ? `Variable {${variableMap[mapKey]}}`
                        : `Variable {% raw %}{{{% endraw %}${v}{% raw %}}}{% endraw %}`;

                    if (method === 'bulk') {
                        html += `
                        <div class="flex items-center gap-3 p-2 bg-white rounded-lg border border-slate-200">
                            <span class="text-[10px] font-bold text-slate-500 w-24">${label}</span>
                            <select name="map_var_${v}" class="flex-1 bg-transparent border-none outline-none text-[10px] font-medium">
                                <option value="">-- Select Column for ${label} --</option>
                                ${currentFileColumns.map(c => `<option value="${c}">${c}</option>`).join('')}
                            </select>
                        </div>
                    `;
                    } else {
                        html += `
                        <div class="flex items-center gap-3 p-2 bg-white rounded-lg border border-slate-200">
                            <span class="text-[10px] font-bold text-slate-500 w-24">${label}</span>
                            <input type="text" name="val_var_${v}" class="flex-1 bg-transparent border-none outline-none text-[10px] font-medium" placeholder="Enter value for ${mapKey}">
                        </div>
                    `;
                    }
                });

                list.innerHTML = html || `<p class="text-[10px] text-slate-400 p-2 italic">This template has no variables.</p>`;
            }

            campaignForm.onsubmit = async (e) => {
                e.preventDefault();
                const method = document.querySelector('input[name="delivery_method"]:checked')?.value || 'bulk';

                if (method === 'bulk' && fileInput.files.length === 0) {
                    return showToast('Please select a file first!', 'error');
                }
                if (method === 'single' && !document.getElementById('singleMobileNumber').value) {
                    return showToast('Please enter a mobile number!', 'error');
                }

                // Media Header Validation
                if (currentHeaderType !== 'NONE' && currentHeaderType !== 'TEXT') {
                    const headerInput = document.querySelector('input[name="val_header"]');
                    const headerSelect = document.querySelector('select[name="map_header"]');
                    
                    if (method === 'single' && headerInput && !headerInput.value.trim() && !document.getElementById('metaMediaId').value) {
                        return showToast(`Please provide a URL or upload a file for the ${currentHeaderType} header!`, 'error');
                    }
                    if (method === 'bulk') {
                        const hasColumn = headerSelect && headerSelect.value && headerSelect.value !== '__UPLOADED__';
                        const isUploaded = headerSelect && headerSelect.value === '__UPLOADED__';
                        const hasFixedUrl = headerInput && headerInput.value.trim();
                        const hasMetaId = document.getElementById('metaMediaId').value;
                        
                        if (isUploaded && !hasMetaId) {
                            return showToast("You selected 'Use Uploaded Campaign Media' but haven't uploaded any file in the Campaign Media section above!", 'error');
                        }
                        
                        if (!hasColumn && !hasFixedUrl && !isUploaded && !hasMetaId) {
                            return showToast(`Please either map a column, provide a fixed URL, or upload a file for the ${currentHeaderType} header!`, 'error');
                        }
                    }
                }

                const formData = new FormData(campaignForm);
                if (method === 'bulk') {
                    formData.append('file', fileInput.files[0]);
                } else {
                    // If single, remove the empty file element entirely to prevent binary upload issues
                    formData.delete("file");
                }

                // Explicitly set media_url (it might have been set by upload)
                formData.set('media_url', document.getElementById('campaignMediaUrl').value);
                const mid = document.getElementById('metaMediaId').value;
                if (mid) formData.set('meta_media_id', mid);

                const msgType = document.querySelector('input[name="msg_type"]:checked').value;

                if (msgType === 'template') {
                    const tName = document.getElementById('templateName').value;
                    if (!tName) return showToast('Please select a template!', 'error');

                    // Gather Mappings
                    const mappings = { vars: {}, header: null };
                    const mappingContainer = document.getElementById('mappingList');

                    // Header Mapping
                    if (method === 'bulk') {
                        const headerSelect = mappingContainer.querySelector('select[name="map_header"]');
                        const headerInput = mappingContainer.querySelector('input[name="val_header"]');
                        if (headerSelect && headerSelect.value && headerSelect.value !== '__UPLOADED__') {
                            mappings.header = { type: 'column', value: headerSelect.value };
                        } else if (headerSelect && headerSelect.value === '__UPLOADED__') {
                            mappings.header = null; // Backend will use meta_media_id automatically
                        } else if (headerInput && headerInput.value.trim() && (!headerSelect || !headerSelect.value)) {
                            mappings.header = { type: 'fixed', value: headerInput.value.trim() };
                        } else if (document.getElementById('metaMediaId').value) {
                            mappings.header = null; // Backend will use meta_media_id automatically
                        }
                    } else {
                        const headerInput = mappingContainer.querySelector('input[name="val_header"]');
                        if (headerInput && headerInput.value.trim()) mappings.header = headerInput.value;
                        else if (document.getElementById('metaMediaId').value) mappings.header = null;
                    }

                    // Var Mappings
                    currentTemplateVars.forEach(v => {
                        if (method === 'bulk') {
                            const sel = mappingContainer.querySelector(`select[name="map_var_${v}"]`);
                            if (sel) mappings.vars[v] = sel.value;
                        } else {
                            const inp = mappingContainer.querySelector(`input[name="val_var_${v}"]`);
                            if (inp) mappings.vars[v] = inp.value;
                        }
                    });

                    formData.append('mappings', JSON.stringify(mappings));
                    formData.append('language_code', selectedTemplateLang);
                    // Include disabled text area value
                    formData.append('message', document.getElementById('messageInput').value);
                } else {
                    formData.set('template_name', '');
                    formData.append('message', document.getElementById('messageInput').value);
                }

                submitBtn.disabled = true;
                const isScheduled = document.getElementById('isScheduled').checked;
                submitBtn.innerHTML = `<span class="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></span> ${isScheduled ? 'Scheduling...' : 'Launching...'}`;

                try {
                    if (isScheduled) {
                        formData.append('scheduled_at', document.getElementById('scheduledAt').value);
                    }
                    const response = await fetch('/upload', { method: 'POST', body: formData });
                    const result = await response.json();
                    if (response.ok) {
                        if (isScheduled) {
                            showToast('Campaign scheduled successfully!', 'success');
                            setTimeout(() => location.reload(), 2000);
                        } else {
                            // Remember the Header URL for next time
                            const tName = document.getElementById('templateName').value;
                            const hInput = document.querySelector('input[name="val_header"]');
                            if (tName && hInput && hInput.value) {
                                localStorage.setItem(`last_header_url_${tName}`, hInput.value);
                            }

                            showToast('Campaign queued!', 'success');
                            document.getElementById('progressCard').classList.remove('hidden');
                            setupSSE();
                            // Reset Button
                            submitBtn.disabled = false;
                            submitBtn.innerText = 'Launch Campaign';
                            // Start processing
                            startBatchProcessing(result.campaign_id);
                        }
                    } else {
                        showToast(result.error || 'Failed to start campaign', 'error');
                        submitBtn.disabled = false;
                        submitBtn.innerText = 'Launch Campaign';
                    }
                } catch (err) {
                    console.error(err);
                    showToast('Network error, try again.', 'error');
                    submitBtn.disabled = false;
                    submitBtn.innerText = 'Launch Campaign';
                }
            };

            function toggleTemplateFields(show) {
                const fields = document.getElementById('templateFields');
                const messageArea = document.getElementById('messageInput').closest('div').parentElement;

                if (show) {
                    fields.classList.remove('hidden');
                    messageArea.classList.add('hidden');
                } else {
                    fields.classList.add('hidden');
                    messageArea.classList.remove('hidden');
                }
                document.getElementById('templateName').required = show;
            }

            function toggleScheduleInput(checked) {
                const area = document.getElementById('scheduleTimeArea');
                const btnText = document.getElementById('submitBtnText');
                if (checked) {
                    area.classList.remove('hidden');
                    btnText.innerText = "Schedule Campaign";
                    // Set default to 1 hour from now
                    const now = new Date();
                    now.setHours(now.getHours() + 1);
                    now.setMinutes(0);
                    document.getElementById('scheduledAt').value = now.toISOString().slice(0, 16);
                } else {
                    area.classList.add('hidden');
                    btnText.innerText = "Launch Campaign";
                }
            }

            // --- Template Wizard Logic ---
            // --- Template Wizard Logic (Rich Editor) ---
            let currentWizStep = 1;
            let isEditMode = false;

            function editTemplate(origin) {
                let templateName;
                if (typeof origin === 'string') {
                    templateName = origin;
                } else {
                    let row = origin.closest('tr');
                    templateName = row.cells[0].innerText.trim();
                }

                let templateData = templatesList.find(t => t.name === templateName);

                if (!templateData) {
                    showToast('Template data not found', 'error');
                    return;
                }

                isEditMode = true;
                currentWizStep = 1;

                // Populate modal
                document.getElementById('wiz_name').value = templateData.name;
                document.getElementById('wiz_name').readOnly = true;

                document.getElementById('wiz_language').value = templateData.language.toLowerCase() === 'en' ? 'en_US' : templateData.language;

                let catEl = document.querySelector(`input[name="wiz_category"][value="${templateData.category}"]`);
                if (catEl) {
                    catEl.checked = true;
                    if (typeof updateWizSubtypes === 'function') updateWizSubtypes(templateData.category);
                }

                // Find body component
                let bodyComp = templateData.components.find(c => c.type === 'BODY');
                if (bodyComp) {
                    document.getElementById('wiz_body').value = bodyComp.text;
                }

                // Header logic
                let headerComp = templateData.components.find(c => c.type === 'HEADER');
                if (headerComp) {
                    document.getElementById('wiz_header_type').value = headerComp.format;
                    if (typeof toggleHeaderInput === 'function') toggleHeaderInput();

                    if (headerComp.format === 'TEXT') {
                        document.getElementById('wiz_header_text').value = headerComp.text || '';
                    } else if (['IMAGE', 'VIDEO', 'DOCUMENT'].includes(headerComp.format)) {
                        if (headerComp.example && headerComp.example.header_handle) {
                            document.getElementById('wiz_header_sample_url').value = headerComp.example.header_handle[0] || "";
                        }
                    }
                } else {
                    document.getElementById('wiz_header_type').value = 'NONE';
                    if (typeof toggleHeaderInput === 'function') toggleHeaderInput();
                }

                // Footer logic
                let footerComp = templateData.components.find(c => c.type === 'FOOTER');
                if (footerComp) {
                    document.getElementById('wiz_footer').value = footerComp.text;
                } else {
                    document.getElementById('wiz_footer').value = '';
                }

                // Retrieve Buttons
                let buttonsComp = templateData.components.find(c => c.type === 'BUTTONS');
                wizButtons = [];
                if (buttonsComp && buttonsComp.buttons) {
                    wizButtons = buttonsComp.buttons;
                }

                if (typeof updateTemplatePreview === 'function') updateTemplatePreview();
                openTemplateModal(true);
            }

            function triggerMediaUpload() {
                document.getElementById('wiz_media_file').click();
            }

            async function handleWizardMedia(input) {
                if (!input.files || !input.files[0]) return;
                const file = input.files[0];
                const type = document.getElementById('wiz_header_type').value;

                // Optional: Basic file type validation
                if (type === 'IMAGE' && !file.type.startsWith('image/')) {
                    return showToast('Please select an image file', 'error');
                }
                if (type === 'VIDEO' && !file.type.startsWith('video/')) {
                    return showToast('Please select a video file', 'error');
                }

                // Size validation
                const sizeMB = file.size / (1024 * 1024);
                const limits = { 'IMAGE': 5, 'VIDEO': 16, 'DOCUMENT': 100 };
                if (limits[type] && sizeMB > limits[type]) {
                    return showToast(`File too large! Max ${limits[type]}MB for ${type.toLowerCase()}s.`, 'error');
                }

                const formData = new FormData();
                formData.append('file', file);

                try {
                    showToast('Uploading media...', 'info');
                    const res = await fetch('/api/upload-media', {
                        method: 'POST',
                        body: formData
                    });
                    const data = await res.json();
                    if (res.ok) {
                        // Prepend origin for absolute URL required by Meta
                        const absoluteUrl = window.location.origin + data.url;
                        document.getElementById('wiz_header_sample_url').value = absoluteUrl;

                        // Show status
                        const statusEl = document.getElementById('wiz_media_status');
                        const nameEl = document.getElementById('wiz_media_filename');
                        if (statusEl && nameEl) {
                            statusEl.classList.remove('hidden');
                            nameEl.innerText = file.name;
                        }

                        updateTemplatePreview();
                        showToast('Media uploaded successfully!', 'success');
                    } else {
                        showToast(data.error || 'Upload failed', 'error');
                    }
                } catch (err) {
                    showToast('Upload error', 'error');
                }
            }

            async function handleCampaignMedia(input) {
                if (!input.files || !input.files[0]) return;
                const file = input.files[0];

                // Basic generic size validation (100MB max for documents, lower for others is handled by Meta but we check 100MB total)
                if (file.size > 100 * 1024 * 1024) {
                    return showToast('File too large! Max 100MB allowed.', 'error');
                }

                const formData = new FormData();
                formData.append('file', file);

                try {
                    showToast('Uploading campaign media...', 'info');
                    const res = await fetch('/api/upload-media', { method: 'POST', body: formData });
                    const data = await res.json();
                    if (res.ok) {
                        const absoluteUrl = window.location.origin + data.url;
                        document.getElementById('campaignMediaUrl').value = absoluteUrl;
                        if (data.meta_media_id) {
                            document.getElementById('metaMediaId').value = data.meta_media_id;
                            console.log("DEBUG: Meta ID captured:", data.meta_media_id);
                        }
                        
                        // UI Feedback
                        const statusEl = document.getElementById('campaignMediaStatus');
                        const nameEl = document.getElementById('campaignMediaFilename');
                        if (statusEl && nameEl) {
                            statusEl.classList.remove('hidden');
                            nameEl.innerText = file.name;
                        }

                        // Auto-select "Use Uploaded" in mapping if applicable
                        const headerMap = document.getElementById('bulk_header_map');
                        if (headerMap) {
                            headerMap.value = '__UPLOADED__';
                            // Trigger the onchange logic manually
                            const headerInput = document.querySelector('input[name="val_header"]');
                            if (headerInput) headerInput.disabled = true;
                        }

                        showToast('Media attached to campaign!', 'success');
                    } else {
                        showToast(data.error || 'Upload failed', 'error');
                    }
                } catch (err) {
                    showToast('Upload error', 'error');
                }
            }
            let wizButtons = [];

            function openTemplateModal(fromEdit = false) {
                currentWizStep = 1;
                wizButtons = [];
                if (!fromEdit) {
                    isEditMode = false;
                    document.getElementById('wiz_name').value = '';
                    document.getElementById('wiz_name').readOnly = false;
                    document.getElementById('wiz_body').value = '';
                    document.getElementById('wiz_header_text').value = '';
                    document.getElementById('wiz_footer').value = '';
                    if (typeof updateTemplatePreview === 'function') updateTemplatePreview();
                }
                document.getElementById('templateModal').classList.remove('hidden');
                document.getElementById('templateModal').classList.add('flex');
                goToStep1();
            }

            function closeTemplateModal() {
                document.getElementById('templateModal').classList.add('hidden');
                document.getElementById('templateModal').classList.remove('flex');
            }

            function goToStep1() {
                currentWizStep = 1;
                document.getElementById('wizardStepDot').innerText = "1";
                document.getElementById('wizardTitle').innerText = "Set up your template";
                document.getElementById('templateStep1').classList.remove('hidden');
                document.getElementById('templateStep2').classList.add('hidden');
            }

            function updateWizSubtypes(category) {
                const area = document.getElementById('wizSubtypeArea');
                if (!area) return;

                if (category === 'AUTHENTICATION') {
                    area.innerHTML = `
                    <label class="flex items-start gap-4 p-4 rounded-2xl border-2 border-indigo-100 bg-indigo-50/30">
                        <input type="radio" name="wiz_subtype" value="OTP" checked class="mt-1 w-4 h-4 text-indigo-600">
                        <div>
                            <p class="text-sm font-bold text-indigo-800">One-Time Password</p>
                            <p class="text-xs text-indigo-400">Send codes to verify your customers' identity.</p>
                        </div>
                    </label>
                `;
                } else {
                    area.innerHTML = `
                    <label class="flex items-start gap-4 p-4 rounded-2xl border-2 border-green-100 bg-green-50/30">
                        <input type="radio" name="wiz_subtype" value="DEFAULT" checked class="mt-1 w-4 h-4 text-green-600">
                        <div>
                            <p class="text-sm font-bold text-green-800">Default</p>
                            <p class="text-xs text-green-400">Standard message with media and buttons.</p>
                        </div>
                    </label>
                    <label class="flex items-start gap-4 p-4 rounded-2xl border border-slate-100 hover:bg-slate-50 transition-all cursor-pointer">
                        <input type="radio" name="wiz_subtype" value="CATALOG" class="mt-1 w-4 h-4 text-green-600">
                        <div>
                            <p class="text-sm font-bold text-slate-800">Catalogue</p>
                            <p class="text-xs text-slate-400">Showcase your products to your customers.</p>
                        </div>
                    </label>
                `;
                }
            }

            function goToStep2() {
                const type = document.getElementById('wiz_template_type').value;
                const headerSelect = document.getElementById('wiz_header_type');

                // Auto-configure header based on type
                if (type === 'STANDARD') {
                    if (headerSelect) headerSelect.value = 'NONE';
                } else if (type === 'MEDIA') {
                    if (headerSelect) headerSelect.value = 'IMAGE';
                }
                if (typeof toggleHeaderInput === 'function') toggleHeaderInput();

                document.getElementById('wizardStepDot').innerText = "2";
                document.getElementById('wizardTitle').innerText = "Edit template";
                document.getElementById('templateStep1').classList.add('hidden');
                document.getElementById('templateStep2').classList.remove('hidden');
                updateTemplatePreview();
                renderWizButtons();
            }

            function updateTemplatePreview() {
                const name = document.getElementById('wiz_name').value || 'New Template';
                const templateType = document.getElementById('wiz_template_type').value;
                const headerType = document.getElementById('wiz_header_type').value;
                const headerText = document.getElementById('wiz_header_text').value;
                const bodyText = document.getElementById('wiz_body').value || 'Your template message will appear here...';
                const footerText = document.getElementById('wiz_footer').value;
                const mediaUrl = document.getElementById('wiz_header_sample_url').value;

                // Update Header Name
                document.getElementById('preview_header_name').innerText = name;

                // Handle Header Preview
                const headerArea = document.getElementById('prev_header_area');
                const headerTextArea = document.getElementById('prev_header_text');
                const headerMediaArea = document.getElementById('prev_header_media');
                const mediaImg = document.getElementById('prev_media_img');
                const videoPrev = document.getElementById('prev_media_video');
                const mediaPlaceholder = document.getElementById('prev_media_placeholder');

                // Reset
                headerArea.classList.add('hidden');
                headerTextArea.classList.add('hidden');
                headerMediaArea.classList.add('hidden');
                mediaImg.classList.add('hidden');
                if (videoPrev) videoPrev.classList.add('hidden');
                mediaPlaceholder.classList.add('hidden');

                if (templateType === 'CAROUSEL') {
                    headerArea.classList.remove('hidden');
                    headerMediaArea.classList.remove('hidden');
                    mediaPlaceholder.classList.remove('hidden');
                    mediaPlaceholder.innerHTML = `
                    <div class="flex flex-col items-center gap-1 p-4">
                        <svg class="w-8 h-8 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path></svg>
                        <span class="text-[8px] font-bold">CAROUSEL (MULTIPLES CARDS)</span>
                    </div>
                `;
                } else if (headerType === 'TEXT' && headerText) {
                    headerArea.classList.remove('hidden');
                    headerTextArea.classList.remove('hidden');
                    headerTextArea.innerText = headerText;
                } else if (['IMAGE', 'VIDEO', 'DOCUMENT'].includes(headerType)) {
                    headerArea.classList.remove('hidden');
                    headerMediaArea.classList.remove('hidden');

                    if (mediaUrl) {
                        if (headerType === 'IMAGE') {
                            mediaImg.src = mediaUrl;
                            mediaImg.classList.remove('hidden');
                        } else if (headerType === 'VIDEO') {
                            if (videoPrev) {
                                videoPrev.src = mediaUrl;
                                videoPrev.classList.remove('hidden');
                            }
                        } else {
                            mediaPlaceholder.classList.remove('hidden');
                        }
                    } else {
                        mediaPlaceholder.classList.remove('hidden');
                    }
                }

                // Update Body Preview (Apply basic formatting for preview)
                let formattedBody = bodyText
                    .replace(/\*(.*?)\*/g, '<b>$1</b>')
                    .replace(/_(.*?)_/g, '<i>$1</i>')
                    .replace(/~(.*?)~/g, '<strike>$1</strike>')
                    .replace(/[\{\[](.*?)[\}\]]/g, '<span class="text-indigo-500 font-bold">{' + '{$1}' + '}</span>');

                document.getElementById('prev_body_text').innerHTML = formattedBody;

                // Update Footer Preview
                const footerEl = document.getElementById('prev_footer_text');
                if (footerText) {
                    footerEl.innerText = footerText;
                    footerEl.classList.remove('hidden');
                } else {
                    footerEl.classList.add('hidden');
                }

                // Update Buttons Preview
                const btnsArea = document.getElementById('prev_buttons_area');
                if (wizButtons.length > 0) {
                    btnsArea.classList.remove('hidden');
                    btnsArea.innerHTML = wizButtons.map(btn => `
                    <div class="py-2 text-center text-[10px] font-bold text-indigo-600 bg-white/50 flex items-center justify-center gap-1.5">
                        ${btn.type === 'PHONE_NUMBER' ? '<svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20"><path d="M2 3a1 1 0 011-1h2.153a1 1 0 01.986.836l.74 4.435a1 1 0 01-.54 1.06l-1.548.773a11.037 11.037 0 005.105 5.105l.774-1.548a1 1 0 011.059-.54l4.435.74a1 1 0 01.836.986V17a1 1 0 01-1 1h-2C7.82 18 2 12.18 2 5V3z"></path></svg>' : ''}
                        ${btn.type === 'URL' ? '<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>' : ''}
                        ${btn.text || 'Button Label'}
                    </div>
                `).join('');
                } else {
                    btnsArea.classList.add('hidden');
                }
            }

            function insertWizVariable() {
                const textarea = document.getElementById('wiz_body');
                const start = textarea.selectionStart;
                const end = textarea.selectionEnd;
                const text = textarea.value;
                const varName = prompt("Enter variable name (e.g. name, order_id):", "name") || "var";
                const insertion = `{${varName}}`;
                textarea.value = text.substring(0, start) + insertion + text.substring(end);
                textarea.focus();
                textarea.selectionStart = textarea.selectionEnd = start + insertion.length;
                updateTemplatePreview();
            }

            function formatWizText(char) {
                const textarea = document.getElementById('wiz_body');
                const start = textarea.selectionStart;
                const end = textarea.selectionEnd;
                const selected = textarea.value.substring(start, end);
                if (!selected) return;
                const insertion = `${char}${selected}${char}`;
                textarea.value = textarea.value.substring(0, start) + insertion + textarea.value.substring(end);
                textarea.focus();
                updateTemplatePreview();
            }

            function addWizButtonRow() {
                if (wizButtons.length >= 3) return showToast('Maximum 3 buttons allowed', 'error');
                wizButtons.push({ type: 'QUICK_REPLY', text: '', url_type: 'STATIC', url: '', phone: '' });
                renderWizButtons();
                updateTemplatePreview();
            }

            function removeWizButtonRow(index) {
                wizButtons.splice(index, 1);
                renderWizButtons();
                updateTemplatePreview();
            }

            function renderWizButtons() {
                const list = document.getElementById('wiz_buttons_list');
                list.innerHTML = wizButtons.map((btn, i) => `
                <div class="p-4 bg-white rounded-2xl border border-slate-200 space-y-3 animate-in fade-in slide-in-from-bottom-2 duration-200">
                    <div class="flex items-center justify-between">
                        <select onchange="updateBtnType(${i}, this.value)" class="bg-slate-50 px-3 py-1.5 rounded-lg text-xs font-bold outline-none border border-slate-200">
                            <option value="QUICK_REPLY" ${btn.type === 'QUICK_REPLY' ? 'selected' : ''}>Quick Reply</option>
                            <option value="PHONE_NUMBER" ${btn.type === 'PHONE_NUMBER' ? 'selected' : ''}>Call</option>
                            <option value="URL" ${btn.type === 'URL' ? 'selected' : ''}>Visit URL</option>
                        </select>
                        <button onclick="removeWizButtonRow(${i})" class="text-rose-400 hover:text-rose-600 transition-colors p-1.5 hover:bg-rose-50 rounded-lg">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                        </button>
                    </div>

                    <div class="space-y-3">
                        ${btn.type === 'URL' ? `
                            <div class="grid grid-cols-4 gap-3 items-end">
                                <div class="col-span-1">
                                    <label class="block text-[10px] font-bold text-slate-400 mb-1 uppercase tracking-wider">URL Type:</label>
                                    <select onchange="wizButtons[${i}].url_type = this.value; renderWizButtons(); updateTemplatePreview()" class="w-full bg-slate-50 px-3 py-2 rounded-xl text-xs font-medium border border-slate-200 outline-none">
                                        <option value="STATIC" ${btn.url_type === 'STATIC' ? 'selected' : ''}>Static</option>
                                        <option value="DYNAMIC" ${btn.url_type === 'DYNAMIC' ? 'selected' : ''}>Dynamic</option>
                                    </select>
                                </div>
                                <div class="col-span-3">
                                    <div class="flex h-10 shadow-sm">
                                        <div class="bg-rose-500 text-white px-4 flex items-center rounded-l-xl text-xs font-bold whitespace-nowrap min-w-[100px]">
                                            <input type="text" value="${btn.text}" oninput="wizButtons[${i}].text = this.value; updateTemplatePreview()" placeholder="Visit Now" class="bg-transparent border-none outline-none text-white placeholder-rose-200 w-full">
                                        </div>
                                        <input type="text" value="${btn.url}" oninput="wizButtons[${i}].url = this.value; updateTemplatePreview()" placeholder="https://example.com" class="flex-1 bg-white px-4 border border-slate-200 border-l-0 rounded-r-xl text-xs font-medium outline-none focus:ring-1 focus:ring-indigo-500">
                                    </div>
                                </div>
                            </div>
                        ` : `
                            <div class="flex items-center gap-3">
                                <div class="flex-1">
                                    <label class="block text-[10px] font-bold text-slate-400 mb-1 uppercase tracking-wider">Button Label:</label>
                                    <input type="text" value="${btn.text}" oninput="wizButtons[${i}].text = this.value; updateTemplatePreview()" placeholder="Enter label..." class="w-full bg-slate-50 px-4 py-2 rounded-xl text-xs font-bold border border-slate-200 outline-none focus:ring-1 focus:ring-indigo-500">
                                </div>
                                ${btn.type === 'PHONE_NUMBER' ? `
                                    <div class="w-1/3">
                                        <label class="block text-[10px] font-bold text-slate-400 mb-1 uppercase tracking-wider">Phone:</label>
                                        <input type="text" value="${btn.phone || ''}" oninput="wizButtons[${i}].phone = this.value; updateTemplatePreview()" placeholder="+91..." class="w-full bg-slate-50 px-4 py-2 rounded-xl text-xs font-medium border border-slate-200 outline-none focus:ring-1 focus:ring-indigo-500">
                                    </div>
                                ` : ''}
                            </div>
                        `}
                    </div>
                </div>
            `).join('');
            }

            function updateBtnType(index, type) {
                wizButtons[index].type = type;
                renderWizButtons();
                updateTemplatePreview();
            }

            function toggleWizMediaSection() {
                const mediaType = document.getElementById('wiz_media_type').value;
                const mediaInfo = document.getElementById('headerMediaInfo');
                const headerTextSection = document.getElementById('headerTextSection');
                const headerTypeInput = document.getElementById('wiz_header_type');
                const headerTextInput = document.getElementById('wiz_header_text');

                if (mediaType === 'NONE') {
                    mediaInfo.classList.add('hidden');
                    headerTextSection.classList.remove('hidden');
                    headerTypeInput.value = headerTextInput.value.trim() ? 'TEXT' : 'NONE';
                } else {
                    mediaInfo.classList.remove('hidden');
                    headerTextSection.classList.add('hidden');
                    headerTypeInput.value = mediaType;
                    headerTextInput.value = '';

                    const sizeLabel = document.getElementById('wiz_media_size_label');
                    if (mediaType === 'IMAGE') sizeLabel.innerText = "Max size: 5 MB";
                    else if (mediaType === 'VIDEO') sizeLabel.innerText = "Max size: 16 MB";
                    else if (mediaType === 'DOCUMENT') sizeLabel.innerText = "Max size: 100 MB";
                    else sizeLabel.innerText = "";
                }
                updateTemplatePreview();
            }

            async function submitWizardTemplate() {
                let name = document.getElementById('wiz_name').value.trim();
                if (!name) return showToast('Template name is required', 'error');
                // Final safety check for name
                name = name.toLowerCase().replace(/[^a-z0-9_]/g, '_');
                document.getElementById('wiz_name').value = name;

                const categoryRadio = document.querySelector('input[name="wiz_category"]:checked');
                const subtypeRadio = document.querySelector('input[name="wiz_subtype"]:checked');
                if (!categoryRadio || !subtypeRadio) return showToast('Please select category and type', 'error');

                const category = categoryRadio.value;
                const subtype = subtypeRadio.value;
                const language = document.getElementById('wiz_language').value;
                let body = document.getElementById('wiz_body').value;
                const footer = document.getElementById('wiz_footer').value;
                const headerType = document.getElementById('wiz_header_type').value;
                const headerText = document.getElementById('wiz_header_text').value;
                const sampleUrl = document.getElementById('wiz_header_sample_url')?.value || '';

                // Validation: Ensure buttons have text
                for (let b of wizButtons) {
                    if (!b.text) return showToast('All buttons must have a label', 'error');
                    if (b.type === 'PHONE_NUMBER' && !b.phone) return showToast('Phone number is required for Call button', 'error');
                    if (b.type === 'URL' && !b.url) return showToast('URL is required for Visit Website button', 'error');
                }

                // Transformation: {name} -> {{1}}
                const variableMap = {};
                let varIndex = 1;
                const varRegex = /[\{\[](\w+)[\}\]]/g;
                const seenVars = new Map();

                const transformedBody = body.replace(varRegex, (match, varName) => {
                    if (!seenVars.has(varName)) {
                        seenVars.set(varName, varIndex++);
                    }
                    const idx = seenVars.get(varName);
                    variableMap[idx] = varName;
                    return `{% raw %}{{{% endraw %}${idx}{% raw %}}}{% endraw %}`;
                });

                const submitBtn = document.getElementById('saveTmplBtn');
                const originalText = submitBtn.innerText;
                submitBtn.disabled = true;
                submitBtn.innerHTML = `<span class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></span> Submitting...`;

                const formData = new FormData();
                formData.append('name', name);
                formData.append('category', category);
                formData.append('subtype', subtype);
                formData.append('language', language);
                formData.append('content', transformedBody);
                formData.append('footer', footer);
                formData.append('header_type', headerType);
                formData.append('header_text', headerType === 'TEXT' ? headerText : (['IMAGE', 'VIDEO', 'DOCUMENT'].includes(headerType) ? sampleUrl : ''));

                // Process Buttons for Dynamic URL support
                const processedButtons = wizButtons.map(b => {
                    let btn = { ...b };
                    if (btn.type === 'URL' && btn.url_type === 'DYNAMIC') {
                        if (!btn.url.includes('{% raw %}{{{% endraw %}1{% raw %}}}{% endraw %}')) {
                            btn.url = btn.url.endsWith('/') ? btn.url + '{% raw %}{{{% endraw %}1{% raw %}}}{% endraw %}' : btn.url + '/{% raw %}{{{% endraw %}1{% raw %}}}{% endraw %}';
                        }
                    }
                    return btn;
                });
                formData.append('buttons', JSON.stringify(processedButtons));
                formData.append('variable_map', JSON.stringify(variableMap));

                try {
                    const response = await fetch('/api/templates/create-complex', { method: 'POST', body: formData });
                    const result = await response.json();
                    if (response.ok) {
                        showToast('Template created successfully!', 'success');
                        closeTemplateModal();
                        // Successfully created, reload to show in list
                        setTimeout(() => location.reload(), 1000);
                    } else {
                        showToast(result.error || 'Failed to create template', 'error');
                    }
                } catch (err) {
                    showToast('Network error', 'error');
                } finally {
                    submitBtn.disabled = false;
                    submitBtn.innerText = originalText;
                }
            }

            const previewModal = document.getElementById('previewModal');
            const previewContent = document.getElementById('previewMessageContent');

            function openPreviewModal(template) {
                const modal = document.getElementById('previewModal');
                const sendBtn = document.getElementById('previewSendBtn');

                const t = typeof template === 'string' ? { content: template } : template;
                document.getElementById('view_contact_name').innerText = t.name ? t.name : "WhatsApp";

                const statusBadge = document.getElementById('view_status_badge');
                if (t.status) {
                    statusBadge.innerText = t.status.toUpperCase();
                    statusBadge.className = targetStatusClass(t.status);
                    statusBadge.classList.remove('hidden');
                } else {
                    statusBadge.classList.add('hidden');
                }

                // Extract components
                const comps = typeof t.components === 'string' ? JSON.parse(t.components) : (t.components || []);
                const header = comps.find(c => c.type === 'HEADER');
                const body = comps.find(c => c.type === 'BODY') || { text: t.content || '' };
                const footer = comps.find(c => c.type === 'FOOTER');
                const buttonsComp = comps.find(c => c.type === 'BUTTONS');

                // Text formatting helper
                const formatWA = (text) => {
                    if (!text) return '';
                    return text
                        .replace(/\*(.*?)\*/g, '<b>$1</b>')
                        .replace(/_(.*?)_/g, '<i>$1</i>')
                        .replace(/~(.*?)~/g, '<strike>$1</strike>')
                        .replace(/\{\{(\d+)\}\}/g, '<span class="text-indigo-600 bg-indigo-50 px-1 rounded">[$1]</span>');
                };

                // Header
                const hArea = document.getElementById('view_header_area');
                const hText = document.getElementById('view_header_text');
                const hMedia = document.getElementById('view_media_area');
                const hIcon = document.getElementById('view_media_icon');
                const hImg = document.getElementById('view_media_img');
                const hLabel = document.getElementById('view_media_label');
                const hPath = document.getElementById('view_media_svg_path');

                hText.classList.add('hidden');
                hMedia.classList.add('hidden');
                hIcon.classList.remove('hidden');
                hImg.classList.add('hidden');
                hImg.src = '';

                if (header && header.format) {
                    hArea.classList.remove('hidden');
                    if (header.format === 'TEXT') {
                        hText.innerHTML = formatWA(header.text || '');
                        hText.classList.remove('hidden');
                    } else if (header.format === 'IMAGE' || header.format === 'VIDEO' || header.format === 'DOCUMENT') {
                        hMedia.classList.remove('hidden');
                        hLabel.innerText = header.format + ' CONTENT';

                        if (header.format === 'IMAGE') {
                            hPath.setAttribute('d', 'M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z');
                            if (header.example) {
                                const previewUrl = header.example._original_url || (header.example.header_handle ? header.example.header_handle[0] : null);
                                if (previewUrl && previewUrl.startsWith('http')) {
                                    hImg.src = previewUrl;
                                    hImg.classList.remove('hidden');
                                    hIcon.classList.add('hidden');
                                }
                            }
                        } else if (header.format === 'VIDEO') {
                            hPath.setAttribute('d', 'M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z M21 12a9 9 0 11-18 0 9 9 0 0118 0z');
                        } else {
                            hPath.setAttribute('d', 'M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z');
                        }
                    }
                } else {
                    hArea.classList.add('hidden');
                }

                // Body
                document.getElementById('view_body_text').innerHTML = formatWA(body.text);

                // Footer
                const fText = document.getElementById('view_footer_text');
                if (footer && footer.text) {
                    fText.innerText = footer.text;
                    fText.classList.remove('hidden');
                } else {
                    fText.classList.add('hidden');
                }

                // Buttons
                const bArea = document.getElementById('view_buttons_area');
                bArea.innerHTML = '';
                if (buttonsComp && buttonsComp.buttons && buttonsComp.buttons.length > 0) {
                    bArea.classList.remove('hidden');
                    buttonsComp.buttons.forEach(btn => {
                        let icon = '';
                        if (btn.type === 'PHONE_NUMBER') icon = '<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"></path></svg>';
                        else if (btn.type === 'URL') icon = '<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>';
                        else icon = '<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6"></path></svg>';

                        bArea.innerHTML += `
                        <div class="py-2.5 text-center text-[#027eb5] text-xs font-medium cursor-pointer flex items-center justify-center gap-1.5 hover:bg-[#d9dbdf] transition-colors">
                            ${icon} ${btn.text}
                        </div>
                    `;
                    });
                } else {
                    bArea.classList.add('hidden');
                }

                // Send Button Logic
                if (sendBtn) {
                    if (t.name) {
                        sendBtn.disabled = false;
                        sendBtn.classList.remove('opacity-50');
                        sendBtn.onclick = () => { closePreviewModal(); sendChatTemplate(t.name); };
                    } else {
                        sendBtn.disabled = true;
                        sendBtn.classList.add('opacity-50');
                        sendBtn.onclick = null;
                    }

                    const footerArea = sendBtn.parentElement;
                    if (footerArea) {
                        if (t.isTemplateTab) {
                            footerArea.classList.add('hidden');
                        } else {
                            footerArea.classList.remove('hidden');
                            footerArea.classList.add('flex');
                        }
                    }
                }

                modal.classList.remove('hidden');
                modal.classList.add('flex');
            }

            function targetStatusClass(status) {
                const s = (status || '').toLowerCase();
                return `px-2 py-0.5 rounded text-[8px] font-bold uppercase tracking-widest ${s === 'approved' ? 'bg-emerald-100 text-emerald-700' : (s === 'rejected' ? 'bg-rose-100 text-rose-700' : 'bg-amber-100 text-amber-700')}`;
            }

            function closePreviewModal() {
                const modal = document.getElementById('previewModal');
                modal.classList.add('hidden');
                modal.classList.remove('flex');
            }

            async function syncTemplates() {
                const btn = document.getElementById('syncBtn');
                btn.innerHTML = `<span class="animate-spin rounded-full h-4 w-4 border-b-2 border-green-600"></span> Syncing...`;
                btn.disabled = true;
                try {
                    const response = await fetch('/templates/sync', { method: 'POST' });
                    const result = await response.json();
                    if (response.ok) {
                        showToast(result.message, 'success');
                        setTimeout(() => location.reload(), 1500);
                    } else {
                        showToast('Sync failed', 'error');
                    }
                } catch (err) { showToast('Network error during sync', 'error'); }
                finally {
                    btn.disabled = false;
                    btn.innerHTML = `Sync Meta`;
                }
            }

            // ───── OTP Template Modal ─────
            function openOtpModal() {
                const modal = document.getElementById('otpTemplateModal');
                modal.classList.remove('hidden');
                modal.classList.add('flex');
                // Reset fields
                document.getElementById('otp_name').value = '';
                document.getElementById('otp_language').value = 'en_US';
                document.getElementById('otp_security').checked = false;
                document.getElementById('otp_expiry').value = '10';
                updateOtpPreview();
            }

            function closeOtpModal() {
                const modal = document.getElementById('otpTemplateModal');
                modal.classList.add('hidden');
                modal.classList.remove('flex');
            }

            function updateOtpPreview() {
                const security = document.getElementById('otp_security').checked;
                const expiry = parseInt(document.getElementById('otp_expiry').value) || 0;

                // Security line
                const secEl = document.getElementById('otp_preview_security');
                if (security) {
                    secEl.classList.remove('hidden');
                } else {
                    secEl.classList.add('hidden');
                }

                // Expiry line
                const expEl = document.getElementById('otp_preview_expiry');
                if (expiry > 0) {
                    expEl.classList.remove('hidden');
                    expEl.textContent = `This code expires in ${expiry} minutes.`;
                } else {
                    expEl.classList.add('hidden');
                }
            }

            async function submitOtpTemplate() {
                const name = document.getElementById('otp_name').value.trim();
                if (!name) { showToast('Please enter a template name.', 'error'); return; }

                const btn = document.getElementById('saveOtpBtn');
                btn.disabled = true;
                btn.innerHTML = `<span class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></span> Saving...`;

                const payload = {
                    name: name.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, ''),
                    language: document.getElementById('otp_language').value,
                    add_security_recommendation: document.getElementById('otp_security').checked,
                    code_expiration_minutes: parseInt(document.getElementById('otp_expiry').value) || 0
                };

                try {
                    const response = await fetch('/api/templates/create-otp', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });
                    const result = await response.json();
                    if (response.ok) {
                        showToast(result.message || 'OTP Template submitted!', 'success');
                        closeOtpModal();
                        setTimeout(() => location.reload(), 1800);
                    } else {
                        showToast(result.error || 'Failed to create OTP template.', 'error');
                    }
                } catch (err) {
                    showToast('Network error. Please try again.', 'error');
                } finally {
                    btn.disabled = false;
                    btn.innerHTML = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg> Save OTP Template`;
                }
            }

            // Removed dead templateForm block

            // Auto-populate message input when a template is selected
            document.getElementById('templateName')?.addEventListener('change', (e) => {
                const selectedName = e.target.value;
                const messageInput = document.getElementById('messageInput');
                const customInput = document.getElementById('customTemplateName');

                if (customInput) {
                    if (selectedName === "") {
                        customInput.classList.remove('hidden');
                        customInput.focus();
                    } else {
                        customInput.classList.add('hidden');
                    }
                }

                if (selectedName && templateData[selectedName]) {
                    messageInput.value = templateData[selectedName];
                    showToast(`Loaded content for ${selectedName}`, 'info');
                } else if (!selectedName) {
                    messageInput.value = '';
                }
            });

            // Custom Confirmation Logic
            function showConfirm(title, message, callback) {
                const modal = document.getElementById('confirmModal');
                document.getElementById('confirmTitle').innerText = title;
                document.getElementById('confirmMessage').innerText = message;
                modal.classList.remove('hidden');
                modal.classList.add('flex');

                const confirmBtn = document.getElementById('confirmConfirmBtn');
                const cancelBtn = document.getElementById('confirmCancelBtn');

                const clearButtons = () => {
                    confirmBtn.onclick = null;
                    cancelBtn.onclick = null;
                    modal.classList.add('hidden');
                    modal.classList.remove('flex');
                };

                confirmBtn.onclick = () => { clearButtons(); callback(); };
                cancelBtn.onclick = () => { clearButtons(); };
            }

            async function deleteTemplate(name) {
                showConfirm('Delete Template?', `Are you sure you want to delete "${name}"? This will remove it from both this dashboard and your Meta account.`, async () => {
                    try {
                        const formData = new FormData();
                        formData.append('name', name);
                        const response = await fetch('/api/templates/delete', { method: 'POST', body: formData });
                        if (response.ok) {
                            showToast('Template deleted successfully!', 'success');
                            setTimeout(() => location.reload(), 1000);
                        } else {
                            const res = await response.json();
                            showToast(res.error || 'Failed to delete template', 'error');
                        }
                    } catch (err) { showToast('Error deleting template', 'error'); }
                });
            }

            async function unlinkAccount() {
                showConfirm('Disconnect WhatsApp?', 'This will stop the service but keep you signed in to Facebook for a quick reconnect.', async () => {
                    try {
                        const response = await fetch('/auth/facebook/unlink', { method: 'POST' });
                        if (response.ok) {
                            showToast('WhatsApp disconnected!', 'success');
                            setTimeout(() => location.reload(), 1500);
                        }
                    } catch (err) { showToast('Error disconnecting', 'error'); }
                });
            }

            async function fullLogout() {
                showConfirm('Full Logout & Switch User?', 'This will sign you out of Facebook entirely so a new user can log in with their own credentials.', async () => {
                    try {
                        // 1. Unlink on backend
                        const response = await fetch('/auth/facebook/unlink', { method: 'POST' });

                        // 2. Logout from FB SDK
                        if (typeof FB !== 'undefined') {
                            FB.logout(() => console.log('Facebook session cleared.'));
                        }

                        if (response.ok) {
                            showToast('Logged out successfully!', 'success');
                            setTimeout(() => location.reload(), 1500);
                        }
                    } catch (err) { showToast('Error during logout', 'error'); }
                });
            }

            async function startBatchProcessing(id) {
                let completed = false;
                let retryCount = 0;

                while (!completed) {
                    try {
                        const res = await fetch(`/api/campaign/process-batch/${id}`, { method: 'POST' });
                        if (!res.ok) throw new Error('Batch failed');

                        const data = await res.json();
                        if (data.completed || data.processed === 0) {
                            completed = true;
                        }
                        retryCount = 0; // Reset on success

                        // Small cooldown between batches to keep Vercel happy
                        await new Promise(r => setTimeout(r, 2000));
                    } catch (e) {
                        console.error("Batch processing error:", e);
                        retryCount++;
                        if (retryCount > 10) break; // Stop after 10 consecutive failures
                        await new Promise(r => setTimeout(r, 5000));
                    }
                }
            }

            async function resumeActiveCampaigns() {
                try {
                    const res = await fetch('/api/history');
                    const campaigns = await res.json();
                    const active = campaigns.find(c => c.status === 'Processing' || c.status === 'Pending');
                    if (active) {
                        console.log("Resuming active campaign:", active.id);
                        document.getElementById('progressCard').classList.remove('hidden');
                        setupSSE();
                        startBatchProcessing(active.id);
                    }
                } catch (e) { console.error("Auto-resume error", e); }
            }

            function setupSSE() {
                const eventSource = new EventSource('/events');
                const statusInfo = document.getElementById('statusInfo');
                const statusMessage = document.getElementById('statusMessage');

                eventSource.onmessage = (e) => {
                    const data = JSON.parse(e.data);
                    const lastEventEl = document.getElementById('lastEvent');

                    // Live Status Updates (from Webhooks)
                    if (data.type === 'status_update') {
                        // Update any visible message rows (if we implement a live list)
                        console.log("Live status update received:", data);
                        return;
                    }

                    if (data.is_waiting) {
                        if (lastEventEl) lastEventEl.innerHTML = `<span class="text-amber-600 font-medium italic">${data.status_text}</span>`;
                        return;
                    }

                    // Handle critical errors like Token Expired
                    if (data.is_auth_error) {
                        statusInfo.classList.remove('hidden');
                        statusMessage.innerText = 'Critical: WhatsApp Token Expired. Please reconnect your account.';
                        statusInfo.classList.add('bg-rose-50', 'text-rose-800', 'border-rose-200');
                        showToast('Authentication Error: Token Expired', 'error');
                    }

                    // Handle completion
                    if (data.is_complete) {
                        eventSource.close();
                        document.getElementById('progressBar').style.width = '100%';
                        document.getElementById('progressPercent').innerText = '100%';
                        if (lastEventEl) lastEventEl.innerHTML = `<span class="text-emerald-600 font-bold">Campaign Finished!</span>`;

                        const submitBtn = document.getElementById('submitBtn');
                        if (submitBtn) {
                            submitBtn.disabled = false;
                            submitBtn.innerHTML = `<span>Launch Campaign</span>`;
                        }

                        showToast('Campaign Completed Successfully!', 'success');
                        setTimeout(() => location.reload(), 1500);
                        return;
                    }

                    const progress = Math.round(((data.success + data.failed) / data.total) * 100);
                    document.getElementById('progressBar').style.width = progress + '%';
                    document.getElementById('progressPercent').innerText = progress + '%';
                    document.getElementById('progressCount').innerText = `${data.success + data.failed} / ${data.total}`;
                    document.getElementById('successCount').innerText = data.success;
                    document.getElementById('failedCount').innerText = data.failed;
                    if (lastEventEl) lastEventEl.innerText = `Sent to ${data.last_phone} (${data.last_status})`;
                };
            }
            // Auto-sync on load
            window.addEventListener('load', () => {
                resumeActiveCampaigns();
                const isLinked = "{{ linked_phone }}";
                if (isLinked && isLinked !== "") {
                    const lastSync = localStorage.getItem('lastAutoSync');
                    const now = Date.now();
                    // 5 minute throttle
                    if (!lastSync || (now - lastSync > 300000)) {
                        localStorage.setItem('lastAutoSync', now);
                        setTimeout(() => {
                            console.log("Auto-Syncing Meta Templates...");
                            syncTemplates();
                        }, 2000);
                    }
                }
            });

            // --- WhatsApp Chat Logic ---
            // Global variables already declared at the top of script if needed, 
            // but let's keep them here for this closure.
            var currentChatPhone = null;
            var currentChatAttachment = null;
            var chatTemplatesList = [];
            var chatInterval = null;
            window.chatContactsData = [];
            var currentChatFilter = 'all';

            function toggleChatFilter() {
                const menu = document.getElementById('chatFilterMenu');
                menu.classList.toggle('hidden');
            }

            function setChatFilter(mode) {
                currentChatFilter = mode;
                document.getElementById('chatFilterMenu').classList.add('hidden');
                renderChatContacts();
            }

            function exportChatCSV() {
                document.getElementById('chatFilterMenu').classList.add('hidden');
                if (!window.chatContactsData || window.chatContactsData.length === 0) return;
                const csvContent = "data:text/csv;charset=utf-8,Phone,Unread\n"
                    + window.chatContactsData.map(c => `${c.phone},${c.has_unread ? 'Yes' : 'No'}`).join("\n");
                const encodedUri = encodeURI(csvContent);
                const link = document.createElement("a");
                link.setAttribute("href", encodedUri);
                link.setAttribute("download", "chat_contacts.csv");
                document.body.appendChild(link);
                link.click();
                link.remove();
            }

            async function loadChatContacts() {
                const list = document.getElementById('chatContactList');
                if (!list) return;
                list.innerHTML = `<div class="p-4 text-center text-xs text-slate-400">Loading contacts...</div>`;

                try {
                    const response = await fetch('/api/chat/contacts');
                    if (!response.ok) throw new Error(`API error: ${response.status}`);

                    const contacts = await response.json();
                    if (!Array.isArray(contacts)) throw new Error('Expected array of contacts');

                    window.chatContactsData = contacts;
                    renderChatContacts();

                } catch (err) {
                    console.error("Chat Contact JS Error:", err);
                    list.innerHTML = `<div class="p-4 text-center text-xs text-rose-400">Error loading contacts:<br/>${err.message}</div>`;
                }
            }

            function renderChatContacts() {
                const list = document.getElementById('chatContactList');
                const search = document.getElementById('chatSearch')?.value.toLowerCase() || '';

                if (window.chatContactsData.length === 0) {
                    list.innerHTML = `<div class="p-8 text-center"><p class="text-xs text-slate-400">No conversations yet.</p><p class="text-[10px] text-slate-300 mt-1">Start by sending a campaign!</p></div>`;
                    return;
                }

                let filtered = window.chatContactsData;

                // Apply text search
                if (search) {
                    filtered = filtered.filter(c => c.phone.includes(search));
                }
                // Apply Mode Filter
                if (currentChatFilter === 'unread') {
                    filtered = filtered.filter(c => c.has_unread);
                } else if (currentChatFilter === 'read') {
                    filtered = filtered.filter(c => !c.has_unread);
                }

                if (filtered.length === 0) {
                    list.innerHTML = `<div class="p-4 text-center text-xs text-slate-400">No matching contacts.</div>`;
                    return;
                }

                list.innerHTML = filtered.map(pData => {
                    const phone = pData.phone;
                    const hasUnread = pData.has_unread;
                    const isActive = currentChatPhone === phone;

                    return `
                <button onclick="openChat('${phone}')" class="w-full p-4 flex items-center gap-3 rounded-xl hover:bg-white hover:shadow-sm transition-all text-left ${isActive ? 'bg-white shadow-sm ring-1 ring-slate-100' : ''}">
                    <div class="relative">
                        <div class="w-10 h-10 ${isActive ? 'bg-green-100 text-green-600' : 'bg-slate-200 text-slate-500'} rounded-full flex items-center justify-center font-bold transition-colors">
                            ${phone.slice(-2)}
                        </div>
                        ${hasUnread ? '<span class="absolute -top-1 -right-1 flex h-3 w-3"><span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span><span class="relative inline-flex rounded-full h-3 w-3 bg-green-500 border-2 border-white"></span></span>' : ''}
                    </div>
                    <div class="flex-grow min-w-0">
                        <p class="text-sm font-bold text-slate-800 truncate ${hasUnread ? 'text-green-700' : ''}">${phone}</p>
                        <p class="text-[10px] ${hasUnread ? 'text-green-600 font-bold' : 'text-slate-400'} truncate">${hasUnread ? 'New messages' : 'Click to view chat'}</p>
                    </div>
                </button>
                `;
                }).join('');
            }

            document.getElementById('chatSearch')?.addEventListener('input', renderChatContacts);


            async function openChat(phone) {
                currentChatPhone = phone;
                document.getElementById('chatPlaceholder').classList.add('hidden');
                document.getElementById('activeChat').classList.remove('hidden');
                document.getElementById('activeChat').classList.add('flex');
                document.getElementById('chatDisplayName').innerText = phone;
                document.getElementById('chatInitials').innerText = phone.slice(-2);
                document.getElementById('chatInput').value = '';

                // Mark as read in UI & DB
                const contact = window.chatContactsData.find(c => c.phone === phone);
                if (contact && contact.has_unread) {
                    contact.has_unread = false;
                    renderChatContacts(); // clear unread dot
                    fetch(`/api/chat/read/${phone}`, { method: 'POST' }).catch(e => console.error(e));
                } else {
                    renderChatContacts(); // simply update highlight status
                }

                await loadChatHistory(phone);

                // Auto-refresh chat every 4 seconds
                if (chatInterval) clearInterval(chatInterval);
                chatInterval = setInterval(() => {
                    if (currentChatPhone === phone && !document.getElementById('content-chat').classList.contains('hidden')) {
                        loadChatHistory(phone, true);
                    }
                }, 4000);
            }

            async function loadChatHistory(phone, silent = false) {
                const area = document.getElementById('chatMessagesArea');
                if (!area) return;
                if (!silent) area.innerHTML = `<div class="h-full flex items-center justify-center text-xs text-slate-400">Loading messages...</div>`;

                try {
                    const response = await fetch(`/api/chat/history/${phone}`);
                    const messages = await response.json();

                    const isAtBottom = area.scrollHeight - area.scrollTop <= area.clientHeight + 100;

                    area.innerHTML = messages.map(m => {
                        const isOut = m.direction === 'outbound';
                        const time = formatTimeOnly(m.timestamp);
                        let displayMsg = m.message;

                        // Handle Inbound Media JSON
                        try {
                            if (m.message.trim().startsWith('{') && m.message.trim().endsWith('}')) {
                                const data = JSON.parse(m.message);
                                if (data.is_media) {
                                    const mediaUrl = `/api/chat/media/${data.media_id}`;
                                    if (data.media_type === 'image') {
                                        displayMsg = `<div class="mb-2"><img src="${mediaUrl}" class="rounded-lg max-w-full h-auto cursor-pointer border border-slate-100" onclick="window.open('${mediaUrl}')" loading="lazy" /></div>`;
                                        if (data.caption) displayMsg += `<p class="text-sm">${data.caption}</p>`;
                                    } else if (data.media_type === 'video') {
                                        displayMsg = `<div class="mb-2"><video controls class="rounded-lg max-w-full h-auto border border-slate-100"><source src="${mediaUrl}" type="video/mp4">Your browser does not support the video tag.</video></div>`;
                                        if (data.caption) displayMsg += `<p class="text-sm">${data.caption}</p>`;
                                    } else {
                                        displayMsg = `<div class="flex items-center gap-2 p-2 bg-slate-50 rounded-lg border border-slate-100 mb-2">
                                        <div class="w-8 h-8 bg-indigo-100 text-indigo-600 rounded flex items-center justify-center">
                                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                                        </div>
                                        <div class="flex-1 min-w-0">
                                            <p class="text-[10px] font-bold truncate text-slate-800">${data.filename || 'File'}</p>
                                            <p class="text-[9px] text-slate-400 uppercase">${data.media_type}</p>
                                        </div>
                                        <a href="${mediaUrl}" target="_blank" class="text-indigo-600 hover:text-indigo-800"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a2 2 0 002 2h12a2 2 0 002-2v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg></a>
                                    </div>`;
                                    }
                                }
                            }
                        } catch (e) {
                            // Not media JSON, use as plain text
                            displayMsg = m.message;
                        }

                        return `
                        <div class="flex ${isOut ? 'justify-end' : 'justify-start'} w-full animate-in fade-in slide-in-from-bottom-2 duration-300">
                            <div class="max-w-[80%] min-w-[60px] p-3 rounded-2xl shadow-sm ${isOut ? 'bg-green-600 text-white rounded-tr-none shadow-green-100' : 'bg-white text-slate-800 rounded-tl-none shadow-slate-100'}">
                                <div class="message-content leading-relaxed">${displayMsg}</div>
                                <div class="flex items-center justify-end gap-1 mt-1 opacity-70">
                                    <span class="text-[9px]">${time}</span>
                                    ${isOut ? `<svg class="w-3 h-3" viewBox="0 0 24 24" fill="currentColor"><path d="M22.319 4.319l-1.414-1.414-11.905 11.905-5.319-5.319-1.414 1.414 6.733 6.733 13.319-13.319zm-6.142 0l-1.414-1.414-7.176 7.176 1.414 1.414 7.176-7.176z"/></svg>` : ''}
                                </div>
                            </div>
                        </div>
                    `;
                    }).join('');

                    if (!silent || isAtBottom) area.scrollTop = area.scrollHeight;
                } catch (err) {
                    if (!silent) area.innerHTML = `<div class="p-4 text-center text-rose-500">Failed to load chat</div>`;
                }
            }

            const commonEmojis = ['😀', '😃', '😄', '😁', '😆', '😅', '😂', '🤣', '😊', '😇', '🙂', '🙃', '😉', '😌', '😍', '🥰', '😘', '😗', '😙', '😚', '😋', '😛', '😝', '😜', '🤪', '🤨', '🧐', '🤓', '😎', '🤩', '🥳', '😏', '😒', '😞', '😔', '😟', '😕', '🙁', '☹️', '😣', '😖', '😫', '😩', '🥺', '😢', '😭', '😤', '😠', '😡', '🤬', '🤯', '😳', '🥵', '🥶', '😱', '😨', '😰', '😥', '😓', '🤗', '🤔', '🤭', '🤫', '🤥', '😶', '😐', '😑', '😬', '🙄', '😯', '😦', '😧', '😮', '😲', '🥱', '😴', '🤤', '😪', '😵', '🤐', '🥴', '🤢', '🤮', '🤧', '😷', '🤒', '🤕', '🤑', '🤠'];

            function initEmojiPicker() {
                const grid = document.getElementById('emojiGrid');
                if (grid) {
                    grid.innerHTML = commonEmojis.map(e => `<button onclick="addChatEmoji('${e}')" class="p-1 hover:bg-slate-100 rounded transition-colors">${e}</button>`).join('');
                }
            }
            window.addEventListener('load', initEmojiPicker);

            function toggleChatEmoji() {
                const picker = document.getElementById('chatEmojiPicker');
                const templatePicker = document.getElementById('chatTemplatePicker');
                if (!picker) return;

                if (picker.style.display === 'none' || picker.classList.contains('hidden')) {
                    const grid = document.getElementById('emojiGrid');
                    if (grid && grid.children.length === 0) {
                        initEmojiPicker();
                    }
                    picker.style.display = 'flex';
                    picker.classList.remove('hidden');
                    if (templatePicker) {
                        templatePicker.style.display = 'none';
                        templatePicker.classList.add('hidden');
                    }
                } else {
                    picker.style.display = 'none';
                    picker.classList.add('hidden');
                }
            }

            // chatTemplatesList is already declared above

            async function toggleChatTemplates() {
                const picker = document.getElementById('chatTemplatePicker');
                const emojiPicker = document.getElementById('chatEmojiPicker');
                const isHidden = picker.style.display === 'none' || picker.classList.contains('hidden');

                if (isHidden) {
                    if (!currentChatPhone) return showToast('Please select a contact first', 'error');

                    document.getElementById('pickerTargetPhone').innerText = currentChatPhone;
                    // Close emoji picker
                    if (emojiPicker) {
                        emojiPicker.style.display = 'none';
                        emojiPicker.classList.add('hidden');
                    }

                    // Show picker
                    picker.style.display = 'flex';
                    picker.classList.remove('hidden');
                    const listArea = document.getElementById('chatTemplateList');
                    listArea.innerHTML = '<tr><td colspan="3" class="px-8 py-12 text-center text-slate-400 text-xs italic">Fetching templates...</td></tr>';

                    try {
                        const response = await fetch('/api/templates');
                        if (response.ok) {
                            const data = await response.json();
                            chatTemplatesList = Array.isArray(data) ? data : [];
                        } else {
                            if (typeof templatesList !== 'undefined') chatTemplatesList = templatesList;
                        }
                        renderChatTemplates(chatTemplatesList);
                    } catch (err) {
                        if (typeof templatesList !== 'undefined') chatTemplatesList = templatesList;
                        renderChatTemplates(chatTemplatesList);
                    }
                } else {
                    picker.style.display = 'none';
                    picker.classList.add('hidden');
                }
            }

            function renderChatTemplates(templates) {
                const listArea = document.getElementById('chatTemplateList');
                try {
                    if (!templates || !Array.isArray(templates)) {
                        listArea.innerHTML = '<tr><td colspan="3" class="px-8 py-12 text-center text-rose-500 text-xs">No templates available. Please sync first.</td></tr>';
                        return;
                    }

                    if (templates.length === 0) {
                        listArea.innerHTML = '<tr><td colspan="3" class="px-8 py-12 text-center text-slate-400 text-xs">No templates found in database. Please sync first.</td></tr>';
                        return;
                    }

                    listArea.innerHTML = templates.map(t => {
                        const safeName = String(t.name).replace(/'/g, "\\'");
                        const safeContent = String(t.content || (t.components ? 'Template with components' : 'No content preview')).replace(/"/g, "&quot;");

                        return `
                        <tr class="hover:bg-indigo-50/50 transition-colors">
                            <td class="px-8 py-5">
                                <span class="text-sm font-bold text-slate-800">${t.name}</span>
                                <div class="flex items-center gap-2 mt-1">
                                    <span class="px-1.5 py-0.5 bg-green-100 text-green-700 text-[9px] font-bold rounded uppercase">${t.language}</span>
                                    <span class="text-[9px] text-slate-400 capitalize">${t.category || ''}</span>
                                    <span class="px-1.5 py-0.5 rounded text-[8px] font-bold uppercase tracking-widest ${
                                        String(t.status).toLowerCase() === 'approved' ? 'bg-emerald-100 text-emerald-700' : 
                                        (String(t.status).toLowerCase() === 'rejected' ? 'bg-rose-100 text-rose-700' : 'bg-amber-100 text-amber-700')
                                    }">${t.status || 'UNKNOWN'}</span>
                                </div>
                            </td>
                            <td class="px-8 py-5">
                                <p class="text-xs text-slate-600 line-clamp-2 italic leading-relaxed" title="${safeContent}">"${safeContent}"</p>
                            </td>
                            <td class="px-8 py-5 text-center">
                                <div class="flex items-center justify-center gap-2">
                                    <button onclick="previewChatTemplate('${safeName}')" class="px-3 py-1.5 bg-slate-100 text-slate-600 rounded-lg text-[10px] font-bold hover:bg-slate-200 transition-all border border-slate-200 shadow-sm">Preview</button>
                                    <button onclick="sendChatTemplate('${safeName}')" class="px-4 py-1.5 bg-indigo-600 text-white rounded-lg text-[10px] font-bold hover:bg-indigo-700 transition-all flex items-center gap-1.5 shadow-md shadow-indigo-100">
                                        <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20"><path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z"></path></svg>
                                        Send
                                    </button>
                                </div>
                            </td>
                        </tr>
                    `;
                    }).join('');
                } catch (err) {
                    console.error('Render Templates Error:', err);
                    listArea.innerHTML = '<tr><td colspan="3" class="px-8 py-12 text-center text-rose-500">Error rendering templates.</td></tr>';
                }
            }

            function previewChatTemplate(name) {
                const t = chatTemplatesList.find(temp => temp.name === name);
                if (!t) return;

                // Open the new structured preview modal
                openPreviewModal(t);
            }

            async function sendChatTemplate(name) {
                if (!currentChatPhone) return;

                showConfirm('Send Template?', `Are you sure you want to send template "${name}" to ${currentChatPhone}?`, async () => {
                    toggleChatTemplates();
                    document.getElementById('chatInput').disabled = true;

                    try {
                        const formData = new FormData();
                        formData.append('phone', currentChatPhone);
                        formData.append('template_name', name);
                        formData.append('msg_type', 'template');

                        const t = chatTemplatesList.find(temp => temp.name === name);
                        if (t && t.language) {
                            formData.append('language_code', t.language);
                        }

                        const response = await fetch('/api/chat/send', {
                            method: 'POST',
                            body: formData
                        });

                        const result = await response.json();
                        if (result.wa_id) {
                            showToast('Template sent successfully!', 'success');
                            loadChatHistory(currentChatPhone);
                        } else {
                            showToast('Failed to send template: ' + (result.error || 'Unknown error'), 'error');
                        }
                    } catch (err) {
                        showToast('Network error while sending template', 'error');
                    } finally {
                        document.getElementById('chatInput').disabled = false;
                    }
                });
            }

            function addChatEmoji(char) {
                const input = document.getElementById('chatInput');
                input.value += char;
                input.focus();
            }

            function handleChatAttachment(input) {
                if (input.files && input.files[0]) {
                    const file = input.files[0];
                    currentChatAttachment = file;
                    document.getElementById('chatAttachmentName').innerText = file.name;
                    document.getElementById('chatAttachmentPreview').classList.remove('hidden');
                    document.getElementById('chatEmojiPicker').classList.add('hidden'); // Close emoji picker if open
                }
            }

            function clearChatAttachment() {
                currentChatAttachment = null;
                document.getElementById('chatAttachmentPreview').classList.add('hidden');
                document.getElementById('chatFileInput').value = '';
                document.getElementById('chatDocInput').value = '';
            }

            async function sendChatReply() {
                const input = document.getElementById('chatInput');
                const message = input.value.trim();

                if ((!message && !currentChatAttachment) || !currentChatPhone) return;

                input.value = '';
                input.disabled = true;
                document.getElementById('chatEmojiPicker').classList.add('hidden');

                try {
                    const formData = new FormData();
                    formData.append('phone', currentChatPhone);
                    formData.append('message', message);
                    if (currentChatAttachment) {
                        formData.append('file', currentChatAttachment);
                    }

                    // Clear UI attachment early
                    clearChatAttachment();

                    const response = await fetch('/api/chat/send', {
                        method: 'POST',
                        body: formData
                    });

                    const result = await response.json();
                    if (response.ok) {
                        await loadChatHistory(currentChatPhone);
                    } else {
                        if (result.code === 'WINDOW_CLOSED') {
                            showConfirm('24-Hour Window Closed', `${result.error}\n\nWould you like to open the Template picker?`, () => {
                                toggleChatTemplates();
                            }, 'Open Templates');
                        } else {
                            showToast(result.error || 'Failed to send message', 'error');
                        }
                    }
                } catch (err) {
                    showToast('Network error', 'error');
                } finally {
                    input.disabled = false;
                    input.focus();
                }
            }

            // Filter Chat Contacts
            document.getElementById('chatSearch')?.addEventListener('input', (e) => {
                const q = e.target.value.toLowerCase();
                document.querySelectorAll('#chatContactList button').forEach(btn => {
                    const phone = btn.querySelector('p').innerText;
                    btn.classList.toggle('hidden', !phone.includes(q));
                });
            });

        