async function kirimAbsen() {
    alert("Mendeteksi lokasi..."); // Supaya kamu tahu tombolnya sudah berfungsi
    navigator.geolocation.getCurrentPosition(async (position) => {
        const lat = position.coords.latitude;
        const lon = position.coords.longitude;

        const response = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}`);
        const data = await response.json();
        
        // --- INI YANG MENGUBAH TAMPILAN ---
        const alamat = data.display_name;
        document.getElementById('lokasi-teks').innerText = alamat; 
        // ----------------------------------

        await fetch('/proses-absen-masuk', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({lat: lat, lon: lon, alamat: alamat})
        });
        
        alert("Berhasil absen di: " + alamat);
    });
}