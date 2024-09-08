// script.js

document.getElementById('viewData').addEventListener('click', function() {
    const table = document.getElementById('tableSelect').value;
    const startTime = document.getElementById('start_time').value;
    const endTime = document.getElementById('end_time').value;
    const interval = document.getElementById('interval').value;

    fetch('/fetch_columns', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `table=${table}&start_time=${startTime}&end_time=${endTime}&interval=${interval}`,
    })
    .then(response => response.json())
    .then(data => {
        const columns = data.columns;
        const rows = data.data;
        
        let tableHTML = '<table class="table table-bordered"><thead><tr>';
        columns.forEach(column => {
            tableHTML += `<th>${column}</th>`;
        });
        tableHTML += '</tr></thead><tbody>';
        
        rows.forEach(row => {
            tableHTML += '<tr>';
            row.forEach(cell => {
                tableHTML += `<td>${cell}</td>`;
            });
            tableHTML += '</tr>';
        });
        tableHTML += '</tbody></table>';
        
        document.getElementById('dataView').innerHTML = tableHTML;
    })
    .catch(error => console.error('Error:', error));
});

document.getElementById('generatePDF').addEventListener('click', function() {
    const table = document.getElementById('tableSelect').value;
    const reportName = document.querySelector('#tableSelect option:checked').textContent; // Get report name from selected option
    const startTime = document.getElementById('start_time').value;
    const endTime = document.getElementById('end_time').value;
    const interval = document.getElementById('interval').value;

    fetch('/generate_pdf', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `table=${table}&start_time=${startTime}&end_time=${endTime}&interval=${interval}&report_name=${encodeURIComponent(reportName)}`,
    })
    .then(response => response.blob())
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'report.pdf';
        document.body.appendChild(a);
        a.click();
        a.remove();
    })
    .catch(error => console.error('Error:', error));
});


// Handle CSV download
document.getElementById('generateCSV').addEventListener('click', function() {
    const table = document.getElementById('tableSelect').value;
    const startTime = document.getElementById('start_time').value;
    const endTime = document.getElementById('end_time').value;
    const interval = document.getElementById('interval').value;

    fetch('/generate_csv', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `table=${table}&start_time=${startTime}&end_time=${endTime}&interval=${interval}`,
    })
    .then(response => response.blob())
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'report.csv';
        document.body.appendChild(a);
        a.click();
        a.remove();
    })
    .catch(error => console.error('Error:', error));
});
