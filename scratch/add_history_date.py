import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add date picker to HTML
header_pattern = r"""                <button onclick="loadHistory\(\)" class="p-2 text-slate-400 hover:text-green-600 transition-colors">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                            d="M4 4v5h\.582m15\.356 2A8\.001 8\.001 0 004\.582 9m0 0H9m11 11v-5h-\.581m0 0a8\.003 8\.003 0 01-15\.357-2m15\.357 2H15">
                        </path>
                    </svg>
                </button>"""

new_header = """                <div class="flex items-center gap-4">
                    <div class="relative">
                        <input type="text" id="historyDateRange" class="pl-10 pr-4 py-2 border border-slate-200 rounded-lg text-sm font-medium text-slate-600 bg-white cursor-pointer w-64 shadow-sm" readonly placeholder="All Time (Recent 10)">
                        <svg class="w-5 h-5 text-slate-400 absolute left-3 top-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>
                    </div>
                    <button onclick="loadHistory()" class="p-2 text-slate-400 hover:text-green-600 transition-colors bg-white rounded-lg border border-slate-200 shadow-sm" title="Refresh">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15">
                            </path>
                        </svg>
                    </button>
                </div>"""

content = re.sub(header_pattern, new_header, content)

# 2. Update loadHistory function
load_history_pattern = r"""            async function loadHistory\(\) \{
                const tbody = document\.getElementById\('historyTableBody'\);
                tbody\.innerHTML = `<tr.*?</tr\>`;

                try \{
                    const response = await fetch\('/api/history'\);"""

new_load_history = """            async function loadHistory() {
                const tbody = document.getElementById('historyTableBody');
                tbody.innerHTML = `<tr><td colspan="6" class="px-8 py-12 text-center text-sm text-slate-500 italic">Loading history...</td></tr>`;

                try {
                    let url = '/api/history';
                    const drp = $('#historyDateRange').data('daterangepicker');
                    // Check if datepicker has a value set (meaning user selected a date)
                    if (drp && $('#historyDateRange').val() !== '') {
                        const start = drp.startDate.format('YYYY-MM-DD');
                        const end = drp.endDate.format('YYYY-MM-DD');
                        url += `?start_date=${start}&end_date=${end}`;
                    }

                    const response = await fetch(url);"""

content = re.sub(load_history_pattern, new_load_history, content)

# 3. Add datepicker initialization at the bottom
init_pattern = r"""        \$\(document\)\.ready\(function\(\) \{
            // Set up date range picker
            const start = moment\(\)\.subtract\(6, 'days'\);
            const end = moment\(\);

            function cb\(start, end\) \{
                \$\('#dashboardDateRange'\)\.val\(start\.format\('MMM D, YYYY'\) \+ ' - ' \+ end\.format\('MMM D, YYYY'\)\);
                fetchFilteredDashboard\(start\.format\('YYYY-MM-DD'\), end\.format\('YYYY-MM-DD'\)\);
            \}"""

new_init = """        $(document).ready(function() {
            // Set up date range picker
            const start = moment().subtract(6, 'days');
            const end = moment();

            function cb(start, end) {
                $('#dashboardDateRange').val(start.format('MMM D, YYYY') + ' - ' + end.format('MMM D, YYYY'));
                fetchFilteredDashboard(start.format('YYYY-MM-DD'), end.format('YYYY-MM-DD'));
            }
            
            // History Date Range Picker (Default Empty)
            $('#historyDateRange').daterangepicker({
                autoUpdateInput: false,
                ranges: {
                   'Today': [moment(), moment()],
                   'Yesterday': [moment().subtract(1, 'days'), moment().subtract(1, 'days')],
                   'Last 7 Days': [moment().subtract(6, 'days'), moment()],
                   'Last 30 Days': [moment().subtract(29, 'days'), moment()],
                   'This Month': [moment().startOf('month'), moment().endOf('month')],
                   'Last Month': [moment().subtract(1, 'month').startOf('month'), moment().subtract(1, 'month').endOf('month')]
                }
            });
            
            $('#historyDateRange').on('apply.daterangepicker', function(ev, picker) {
                $(this).val(picker.startDate.format('MMM D, YYYY') + ' - ' + picker.endDate.format('MMM D, YYYY'));
                loadHistory();
            });

            $('#historyDateRange').on('cancel.daterangepicker', function(ev, picker) {
                $(this).val('');
                loadHistory();
            });"""

content = re.sub(init_pattern, new_init, content)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
