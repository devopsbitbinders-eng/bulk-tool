import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

nav_pattern = r'    <!-- Navigation -->\s*<nav class="bg-white border-b border-slate-200 py-4 px-8 mb-4">.*?</nav>'

new_nav = """    <!-- Navigation -->
    <nav class="bg-white border-b border-slate-200 pt-4 mb-4 flex flex-col gap-4">
        <!-- Top Tier: Logo, Auth, Status, Profile -->
        <div class="max-w-7xl mx-auto flex justify-between items-center w-full px-8">
            <div class="flex items-center gap-6">
                <!-- Logo -->
                <img src="/static/logo.png" alt="BulkPulse Logo" class="h-10">
                
                <!-- Facebook Login Button Group -->
                <div class="flex items-center gap-2 border-l border-slate-200 pl-6">
                    <button id="fbLinkBtn" onclick="launchFBLogin()"
                        class="flex items-center gap-2 {% if linked_phone %}bg-emerald-500{% else %}bg-[#1877F2]{% endif %} hover:opacity-90 text-white px-4 py-2 rounded-xl text-xs font-bold transition-all shadow-md"
                        {% if linked_phone %}disabled{% endif %}>
                        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                            <path
                                d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
                        </svg>
                        {% if linked_phone %}Linked ✓{% else %}Connect WhatsApp{% endif %}
                    </button>
                    <button onclick="openManualAuthModal()"
                        class="p-2 text-slate-400 hover:text-indigo-600 transition-colors bg-white rounded-xl border border-slate-100 shadow-sm"
                        title="Manual Credential Setup">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z">
                            </path>
                        </svg>
                    </button>
                    {% if linked_phone %}
                    <div class="flex items-center gap-1">
                        <button onclick="unlinkAccount()"
                            class="p-2 text-slate-400 hover:text-amber-500 transition-colors bg-slate-50 rounded-xl border border-slate-100"
                            title="Disconnect WhatsApp (Keep Login)">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                    d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1">
                                </path>
                            </svg>
                        </button>
                    </div>
                    {% endif %}
                </div>
            </div>

            <div class="flex items-center gap-6">
                <!-- Status -->
                <div class="flex items-center gap-2 px-3 py-1 bg-slate-50 rounded-lg border border-slate-100">
                    <span id="apiStatusDot"
                        class="w-2 h-2 {% if linked_phone %}bg-green-500{% else %}bg-slate-300{% endif %} rounded-full {% if linked_phone %}animate-pulse{% endif %}"></span>
                    <div class="flex flex-col">
                        <span id="apiStatusText" class="text-[10px] font-bold text-slate-600 leading-tight">
                            {% if linked_phone %}ACTIVE: {{ linked_phone }}{% else %}DISCONNECTED{% endif %}
                        </span>
                        {% if linked_phone %}
                        <span class="text-[8px] text-slate-400 font-medium">WABA: {{ waba_id }}</span>
                        {% endif %}
                    </div>
                </div>

                <!-- Profile Dropdown -->
                <div class="relative" id="profile-container">
                    <button onclick="toggleProfileMenu(event)"
                        class="flex items-center gap-2 p-1 pr-3 bg-white hover:bg-slate-50 rounded-full border border-slate-200 transition-all shadow-sm group">
                        <div
                            class="w-8 h-8 rounded-full bg-gradient-to-tr from-indigo-500 to-emerald-500 flex items-center justify-center text-white font-bold text-xs shadow-inner uppercase">
                            {{ username[0] if username else 'U' }}
                        </div>
                        <div class="hidden sm:block text-left overflow-hidden">
                            <p class="text-[9px] text-slate-400 font-medium leading-none mb-0.5">Signed in as</p>
                            <p class="text-[11px] text-slate-700 font-bold leading-none truncate max-w-[80px]"
                                title="{{ username }}">{{ username or 'User' }}</p>
                        </div>
                        <svg class="w-3 h-3 text-slate-400 group-hover:text-slate-600 transition-colors" fill="none"
                            stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7">
                            </path>
                        </svg>
                    </button>
                    <!-- Dropdown Menu -->
                    <div id="profileMenu"
                        class="hidden absolute right-0 mt-3 w-56 bg-white rounded-2xl border border-slate-100 shadow-2xl z-[5000] overflow-hidden">
                        <div class="p-4 bg-slate-50 border-b border-slate-100">
                            <p class="text-[10px] text-slate-400 font-medium uppercase tracking-wider mb-1">User Account
                            </p>
                            <p class="text-sm font-bold text-slate-800 truncate" id="dropdownUsername">{{ username or
                                'User' }}</p>
                        </div>
                        <div class="p-1.5">
                            <a href="/logout"
                                class="flex items-center gap-2.5 px-3.5 py-2.5 text-sm text-rose-500 hover:bg-rose-50 rounded-xl transition-all font-semibold">
                                <span class="p-1.5 bg-rose-100 rounded-lg text-rose-600">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                            d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1">
                                        </path>
                                    </svg>
                                </span>
                                Sign Out
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Bottom Tier: Tabs -->
        <div class="max-w-7xl mx-auto flex gap-6 w-full px-8 mt-2">
            <button onclick="switchTab('campaigns')" id="tab-campaigns"
                class="tab-btn active pb-3 pt-1 font-medium text-sm transition-all text-slate-500 hover:text-slate-800">Campaigns</button>
            <button onclick="switchTab('analytics')" id="tab-analytics"
                class="tab-btn pb-3 pt-1 font-medium text-sm text-slate-500 hover:text-slate-800 transition-all">Analytics</button>
            <button onclick="switchTab('templates')" id="tab-templates"
                class="tab-btn pb-3 pt-1 font-medium text-sm text-slate-500 hover:text-slate-800 transition-all">Templates</button>
            <button onclick="switchTab('history')" id="tab-history"
                class="tab-btn pb-3 pt-1 font-medium text-sm text-slate-500 hover:text-slate-800 transition-all">Sending History</button>
            <button onclick="switchTab('chat')" id="tab-chat"
                class="tab-btn pb-3 pt-1 font-medium text-sm text-slate-500 hover:text-slate-800 transition-all flex items-center gap-1.5">
                Chat
                <span id="unreadBadge" class="hidden w-2 h-2 bg-rose-500 rounded-full animate-pulse"></span>
            </button>
            {% if is_admin %}
            <button onclick="switchTab('admin')" id="tab-admin"
                class="tab-btn pb-3 pt-1 font-medium text-sm text-slate-500 hover:text-slate-800 transition-all flex items-center gap-1.5">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                        d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z">
                    </path>
                </svg>
                Admin
            </button>
            {% endif %}
        </div>
    </nav>"""

content = re.sub(nav_pattern, new_nav, content, flags=re.DOTALL)
with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
