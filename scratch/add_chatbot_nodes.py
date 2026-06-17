import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Expand the Sidebar Palette
palette_pattern = r"""                        <div class="drag-node" draggable="true" ondragstart="drag\(event\)" data-node="send_message">[\s\S]*?Condition \(If/Else\)
                        </div>"""

new_palette = """                        <div class="drag-node" draggable="true" ondragstart="drag(event)" data-node="text_reply">
                            <div class="w-8 h-8 rounded-lg bg-blue-500 text-white flex items-center justify-center"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path></svg></div>
                            Text Reply
                        </div>
                        <div class="drag-node" draggable="true" ondragstart="drag(event)" data-node="text_button">
                            <div class="w-8 h-8 rounded-lg bg-red-500 text-white flex items-center justify-center"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122"></path></svg></div>
                            Text + Button
                        </div>
                        <div class="drag-node" draggable="true" ondragstart="drag(event)" data-node="media_button">
                            <div class="w-8 h-8 rounded-lg bg-indigo-500 text-white flex items-center justify-center"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg></div>
                            Media + Button
                        </div>
                        <div class="drag-node" draggable="true" ondragstart="drag(event)" data-node="text_list">
                            <div class="w-8 h-8 rounded-lg bg-green-500 text-white flex items-center justify-center"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"></path></svg></div>
                            Text + List
                        </div>
                        <div class="drag-node" draggable="true" ondragstart="drag(event)" data-node="url_button">
                            <div class="w-8 h-8 rounded-lg bg-cyan-500 text-white flex items-center justify-center"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"></path></svg></div>
                            URL Button
                        </div>
                        <div class="drag-node" draggable="true" ondragstart="drag(event)" data-node="media_caption">
                            <div class="w-8 h-8 rounded-lg bg-orange-400 text-white flex items-center justify-center"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg></div>
                            Media Caption
                        </div>
                        <div class="drag-node" draggable="true" ondragstart="drag(event)" data-node="request_location">
                            <div class="w-8 h-8 rounded-lg bg-blue-400 text-white flex items-center justify-center"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"></path></svg></div>
                            Request Location
                        </div>
                        <div class="drag-node" draggable="true" ondragstart="drag(event)" data-node="wapp_form">
                            <div class="w-8 h-8 rounded-lg bg-yellow-200 text-yellow-700 flex items-center justify-center"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg></div>
                            WAPP Form
                        </div>
                        <div class="drag-node" draggable="true" ondragstart="drag(event)" data-node="add_group">
                            <div class="w-8 h-8 rounded-lg bg-purple-400 text-white flex items-center justify-center"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path></svg></div>
                            Add to Group
                        </div>
                        <div class="drag-node" draggable="true" ondragstart="drag(event)" data-node="add_tag">
                            <div class="w-8 h-8 rounded-lg bg-yellow-300 text-yellow-800 flex items-center justify-center"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"></path></svg></div>
                            Add to Tag
                        </div>
                        <div class="drag-node" draggable="true" ondragstart="drag(event)" data-node="push_webhook">
                            <div class="w-8 h-8 rounded-lg bg-slate-400 text-white flex items-center justify-center"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"></path></svg></div>
                            Push to Webhook
                        </div>
                        <div class="drag-node" draggable="true" ondragstart="drag(event)" data-node="create_ticket">
                            <div class="w-8 h-8 rounded-lg bg-emerald-400 text-white flex items-center justify-center"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 5v2m0 4v2m0 4v2M5 5a2 2 0 00-2 2v3a2 2 0 110 4v3a2 2 0 002 2h14a2 2 0 002-2v-3a2 2 0 110-4V7a2 2 0 00-2-2H5z"></path></svg></div>
                            Create Ticket
                        </div>
                        <div class="drag-node" draggable="true" ondragstart="drag(event)" data-node="connect_agents">
                            <div class="w-8 h-8 rounded-lg bg-teal-500 text-white flex items-center justify-center"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"></path></svg></div>
                            Connect to Agents
                        </div>
                        <div class="drag-node" draggable="true" ondragstart="drag(event)" data-node="opt_out">
                            <div class="w-8 h-8 rounded-lg bg-rose-600 text-white flex items-center justify-center"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg></div>
                            Opt-out Number
                        </div>
                        <div class="drag-node" draggable="true" ondragstart="drag(event)" data-node="connect_flow">
                            <div class="w-8 h-8 rounded-lg bg-cyan-400 text-white flex items-center justify-center"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"></path></svg></div>
                            Connect to Other Flow
                        </div>"""
content = re.sub(palette_pattern, new_palette, content)


# 2. Expand addNodeToDrawFlow
drawflow_func_pattern = r"""            if\(name === 'start'\) \{[\s\S]*?else if\(name === 'condition'\) \{[\s\S]*?editor\.addNode\('condition', 1, 2, pos_x, pos_y, 'condition', \{ "action": "condition", "condition": "" \}, html\);\s*\}"""

new_drawflow_func = """            if(name === 'start') {
                html = `
                <div class="title-box"><div class="flex items-center gap-2"><div class="w-6 h-6 rounded bg-emerald-100 text-emerald-600 flex items-center justify-center"><svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"></path></svg></div> Start</div></div>
                <div class="box">
                    <label class="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Starting Keyword(s)</label>
                    <input df-keyword type="text" class="w-full text-sm border border-slate-200 rounded p-2 focus:ring-emerald-500 focus:border-emerald-500" placeholder="e.g. Hello, Hi">
                    <p class="text-[10px] text-slate-400 mt-1">Comma separated</p>
                </div>
                `;
                editor.addNode('start', 0, 1, pos_x, pos_y, 'start', { "action": "start", "keyword": "" }, html);
            } 
            else if(name === 'text_reply') {
                html = `
                <div class="title-box"><div class="flex items-center gap-2"><div class="w-6 h-6 rounded bg-blue-500 text-white flex items-center justify-center"><svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5"></path></svg></div> Text Reply</div> <svg class="w-4 h-4" onclick="editor.removeNodeId('node-'+this.parentElement.parentElement.id.slice(5))" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg></div>
                <div class="box">
                    <textarea df-text class="w-full text-sm border border-slate-200 rounded p-2 focus:ring-blue-500 focus:border-blue-500" rows="3" placeholder="Enter reply text..."></textarea>
                </div>
                `;
                editor.addNode('text_reply', 1, 1, pos_x, pos_y, 'text_reply', { "action": "text_reply", "text": "" }, html);
            }
            else if(name === 'text_button') {
                html = `
                <div class="title-box"><div class="flex items-center gap-2"><div class="w-6 h-6 rounded bg-red-500 text-white flex items-center justify-center"><svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 15l-2 5L9 9l11 4-5 2z"></path></svg></div> Text + Button</div> <svg class="w-4 h-4" onclick="editor.removeNodeId('node-'+this.parentElement.parentElement.id.slice(5))" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg></div>
                <div class="box space-y-2">
                    <textarea df-text class="w-full text-sm border border-slate-200 rounded p-2 focus:ring-red-500 focus:border-red-500" rows="2" placeholder="Message text..."></textarea>
                    <input df-btn1 type="text" class="w-full text-sm border border-slate-200 rounded p-2" placeholder="Button 1 text">
                    <input df-btn2 type="text" class="w-full text-sm border border-slate-200 rounded p-2" placeholder="Button 2 text (optional)">
                    <div class="flex justify-between mt-2 text-xs text-slate-400 font-medium px-1"><span>Btn 1</span> <span>Btn 2</span></div>
                </div>
                `;
                editor.addNode('text_button', 1, 2, pos_x, pos_y, 'text_button', { "action": "text_button", "text": "", "btn1": "", "btn2": "" }, html);
            }
            else if(name === 'media_button') {
                html = `
                <div class="title-box"><div class="flex items-center gap-2"><div class="w-6 h-6 rounded bg-indigo-500 text-white flex items-center justify-center"><svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14"></path></svg></div> Media + Button</div> <svg class="w-4 h-4" onclick="editor.removeNodeId('node-'+this.parentElement.parentElement.id.slice(5))" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg></div>
                <div class="box space-y-2">
                    <input df-media_url type="text" class="w-full text-sm border border-slate-200 rounded p-2" placeholder="Media URL (Img/Vid/Doc)">
                    <input df-btn1 type="text" class="w-full text-sm border border-slate-200 rounded p-2" placeholder="Button 1 text">
                    <div class="flex justify-between mt-2 text-xs text-slate-400 font-medium px-1"><span>Btn 1</span></div>
                </div>
                `;
                editor.addNode('media_button', 1, 1, pos_x, pos_y, 'media_button', { "action": "media_button", "media_url": "", "btn1": "" }, html);
            }
            else if(name === 'text_list') {
                html = `
                <div class="title-box"><div class="flex items-center gap-2"><div class="w-6 h-6 rounded bg-green-500 text-white flex items-center justify-center"><svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2"></path></svg></div> Text + List</div> <svg class="w-4 h-4" onclick="editor.removeNodeId('node-'+this.parentElement.parentElement.id.slice(5))" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg></div>
                <div class="box space-y-2">
                    <textarea df-text class="w-full text-sm border border-slate-200 rounded p-2" rows="2" placeholder="Message text..."></textarea>
                    <input df-list_title type="text" class="w-full text-sm border border-slate-200 rounded p-2" placeholder="List Menu Title">
                    <input df-opt1 type="text" class="w-full text-sm border border-slate-200 rounded p-2" placeholder="Option 1">
                    <input df-opt2 type="text" class="w-full text-sm border border-slate-200 rounded p-2" placeholder="Option 2">
                    <div class="flex justify-between mt-2 text-xs text-slate-400 font-medium px-1"><span>Opt 1</span> <span>Opt 2</span></div>
                </div>
                `;
                editor.addNode('text_list', 1, 2, pos_x, pos_y, 'text_list', { "action": "text_list", "text": "", "list_title": "", "opt1": "", "opt2": "" }, html);
            }
            else if(name === 'url_button') {
                html = `
                <div class="title-box"><div class="flex items-center gap-2"><div class="w-6 h-6 rounded bg-cyan-500 text-white flex items-center justify-center"><svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101"></path></svg></div> URL Button</div> <svg class="w-4 h-4" onclick="editor.removeNodeId('node-'+this.parentElement.parentElement.id.slice(5))" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg></div>
                <div class="box space-y-2">
                    <input df-btn_label type="text" class="w-full text-sm border border-slate-200 rounded p-2" placeholder="Button Label">
                    <input df-url type="text" class="w-full text-sm border border-slate-200 rounded p-2" placeholder="https://...">
                </div>
                `;
                editor.addNode('url_button', 1, 1, pos_x, pos_y, 'url_button', { "action": "url_button", "btn_label": "", "url": "" }, html);
            }
            else if(name === 'media_caption') {
                html = `
                <div class="title-box"><div class="flex items-center gap-2"><div class="w-6 h-6 rounded bg-orange-400 text-white flex items-center justify-center"><svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01"></path></svg></div> Media Caption</div> <svg class="w-4 h-4" onclick="editor.removeNodeId('node-'+this.parentElement.parentElement.id.slice(5))" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg></div>
                <div class="box space-y-2">
                    <input df-media_url type="text" class="w-full text-sm border border-slate-200 rounded p-2" placeholder="Media URL">
                    <textarea df-caption class="w-full text-sm border border-slate-200 rounded p-2" rows="2" placeholder="Caption..."></textarea>
                </div>
                `;
                editor.addNode('media_caption', 1, 1, pos_x, pos_y, 'media_caption', { "action": "media_caption", "media_url": "", "caption": "" }, html);
            }
            else if(name === 'request_location') {
                html = `
                <div class="title-box"><div class="flex items-center gap-2"><div class="w-6 h-6 rounded bg-blue-400 text-white flex items-center justify-center"><svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"></path></svg></div> Request Location</div> <svg class="w-4 h-4" onclick="editor.removeNodeId('node-'+this.parentElement.parentElement.id.slice(5))" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg></div>
                <div class="box space-y-2">
                    <input df-text type="text" class="w-full text-sm border border-slate-200 rounded p-2" placeholder="Please share your location">
                </div>
                `;
                editor.addNode('request_location', 1, 1, pos_x, pos_y, 'request_location', { "action": "request_location", "text": "Please share your location" }, html);
            }
            else if(name === 'wapp_form') {
                html = `
                <div class="title-box"><div class="flex items-center gap-2"><div class="w-6 h-6 rounded bg-yellow-200 text-yellow-700 flex items-center justify-center"><svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg></div> WAPP Form</div> <svg class="w-4 h-4" onclick="editor.removeNodeId('node-'+this.parentElement.parentElement.id.slice(5))" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg></div>
                <div class="box space-y-2">
                    <input df-form_id type="text" class="w-full text-sm border border-slate-200 rounded p-2" placeholder="Form ID">
                </div>
                `;
                editor.addNode('wapp_form', 1, 1, pos_x, pos_y, 'wapp_form', { "action": "wapp_form", "form_id": "" }, html);
            }
            else if(name === 'add_group') {
                html = `
                <div class="title-box"><div class="flex items-center gap-2"><div class="w-6 h-6 rounded bg-purple-400 text-white flex items-center justify-center"><svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path></svg></div> Add to Group</div> <svg class="w-4 h-4" onclick="editor.removeNodeId('node-'+this.parentElement.parentElement.id.slice(5))" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg></div>
                <div class="box space-y-2">
                    <input df-group_name type="text" class="w-full text-sm border border-slate-200 rounded p-2" placeholder="Group Name">
                </div>
                `;
                editor.addNode('add_group', 1, 1, pos_x, pos_y, 'add_group', { "action": "add_group", "group_name": "" }, html);
            }
            else if(name === 'add_tag') {
                html = `
                <div class="title-box"><div class="flex items-center gap-2"><div class="w-6 h-6 rounded bg-yellow-300 text-yellow-800 flex items-center justify-center"><svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"></path></svg></div> Add to Tag</div> <svg class="w-4 h-4" onclick="editor.removeNodeId('node-'+this.parentElement.parentElement.id.slice(5))" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg></div>
                <div class="box space-y-2">
                    <input df-tag_name type="text" class="w-full text-sm border border-slate-200 rounded p-2" placeholder="Tag Name">
                </div>
                `;
                editor.addNode('add_tag', 1, 1, pos_x, pos_y, 'add_tag', { "action": "add_tag", "tag_name": "" }, html);
            }
            else if(name === 'push_webhook') {
                html = `
                <div class="title-box"><div class="flex items-center gap-2"><div class="w-6 h-6 rounded bg-slate-400 text-white flex items-center justify-center"><svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"></path></svg></div> Push to Webhook</div> <svg class="w-4 h-4" onclick="editor.removeNodeId('node-'+this.parentElement.parentElement.id.slice(5))" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg></div>
                <div class="box space-y-2">
                    <input df-webhook_url type="text" class="w-full text-sm border border-slate-200 rounded p-2" placeholder="Webhook URL">
                </div>
                `;
                editor.addNode('push_webhook', 1, 1, pos_x, pos_y, 'push_webhook', { "action": "push_webhook", "webhook_url": "" }, html);
            }
            else if(name === 'create_ticket') {
                html = `
                <div class="title-box"><div class="flex items-center gap-2"><div class="w-6 h-6 rounded bg-emerald-400 text-white flex items-center justify-center"><svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 5v2m0 4v2m0 4v2M5 5a2 2 0 00-2 2v3a2 2 0 110 4v3a2 2 0 002 2h14a2 2 0 002-2v-3a2 2 0 110-4V7a2 2 0 00-2-2H5z"></path></svg></div> Create Ticket</div> <svg class="w-4 h-4" onclick="editor.removeNodeId('node-'+this.parentElement.parentElement.id.slice(5))" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg></div>
                <div class="box space-y-2">
                    <input df-department type="text" class="w-full text-sm border border-slate-200 rounded p-2" placeholder="Department">
                </div>
                `;
                editor.addNode('create_ticket', 1, 1, pos_x, pos_y, 'create_ticket', { "action": "create_ticket", "department": "" }, html);
            }
            else if(name === 'connect_agents') {
                html = `
                <div class="title-box"><div class="flex items-center gap-2"><div class="w-6 h-6 rounded bg-teal-500 text-white flex items-center justify-center"><svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"></path></svg></div> Connect Agents</div> <svg class="w-4 h-4" onclick="editor.removeNodeId('node-'+this.parentElement.parentElement.id.slice(5))" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg></div>
                <div class="box space-y-2 text-sm text-slate-500">
                    Routes user to live agents.
                </div>
                `;
                editor.addNode('connect_agents', 1, 1, pos_x, pos_y, 'connect_agents', { "action": "connect_agents" }, html);
            }
            else if(name === 'opt_out') {
                html = `
                <div class="title-box"><div class="flex items-center gap-2"><div class="w-6 h-6 rounded bg-rose-600 text-white flex items-center justify-center"><svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg></div> Opt-out Number</div> <svg class="w-4 h-4" onclick="editor.removeNodeId('node-'+this.parentElement.parentElement.id.slice(5))" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg></div>
                <div class="box space-y-2 text-sm text-slate-500">
                    Stops all future campaigns.
                </div>
                `;
                editor.addNode('opt_out', 1, 1, pos_x, pos_y, 'opt_out', { "action": "opt_out" }, html);
            }
            else if(name === 'connect_flow') {
                html = `
                <div class="title-box"><div class="flex items-center gap-2"><div class="w-6 h-6 rounded bg-cyan-400 text-white flex items-center justify-center"><svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"></path></svg></div> Connect Flow</div> <svg class="w-4 h-4" onclick="editor.removeNodeId('node-'+this.parentElement.parentElement.id.slice(5))" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg></div>
                <div class="box space-y-2">
                    <input df-flow_id type="text" class="w-full text-sm border border-slate-200 rounded p-2" placeholder="Flow ID or Name">
                </div>
                `;
                editor.addNode('connect_flow', 1, 0, pos_x, pos_y, 'connect_flow', { "action": "connect_flow", "flow_id": "" }, html);
            }"""

content = re.sub(drawflow_func_pattern, new_drawflow_func, content)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
