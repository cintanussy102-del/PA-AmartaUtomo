let petaLokasi = null;
let markerLokasi = null;

function tampilkanPeta(lat, lon) {
    const placeholder = document.getElementById('peta-placeholder');
    if (placeholder) placeholder.style.display = 'none';

    if (!petaLokasi) {
        petaLokasi = L.map('peta-lokasi').setView([lat, lon], 17);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap contributors',
            maxZoom: 19
        }).addTo(petaLokasi);
        markerLokasi = L.marker([lat, lon]).addTo(petaLokasi);
    } else {
        petaLokasi.setView([lat, lon], 17);
        markerLokasi.setLatLng([lat, lon]);
    }

    setTimeout(() => petaLokasi.invalidateSize(), 200);
}

async function kirimAbsen() {
    alert("Mendeteksi lokasi...");
    navigator.geolocation.getCurrentPosition(async (position) => {
        const lat = position.coords.latitude;
        const lon = position.coords.longitude;

        tampilkanPeta(lat, lon);

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
            const result = await res.json(); 
            
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