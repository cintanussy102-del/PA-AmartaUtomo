async function kirimAbsen() {
    alert("Mendeteksi lokasi...");
    navigator.geolocation.getCurrentPosition(async (position) => {
        const lat = position.coords.latitude;
        const lon = position.coords.longitude;

        const response = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}`);
        const data = await response.json();
        
        const alamat = data.display_name;
        document.getElementById('lokasi-teks').innerText = alamat; 

        // --- UPDATE: Menangkap respons dari server ---
        const res = await fetch('/proses-absen-masuk', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({lat: lat, lon: lon, alamat: alamat})
        });

        if (res.ok) {
            const result = await res.json(); // Hasil dari app.py (tanggal, jam_masuk, status)
            
            // --- UPDATE: Masukkan baris baru ke tabel ---
            const tableBody = document.querySelector('.amarta-table tbody');
            const newRow = `<tr>
                <td>${result.tanggal}</td>
                <td>${result.jam_masuk}</td>
                <td>-</td>
                <td><span class="status-badge aktif">${result.status}</span></td>
            </tr>`;
            
            // Masukkan ke posisi paling atas tabel
            tableBody.insertAdjacentHTML('afterbegin', newRow);
            
            alert("Berhasil absen masuk pada: " + result.jam_masuk);
        }
    });
}