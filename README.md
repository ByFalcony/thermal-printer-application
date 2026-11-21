<p align="center">
  <img src="icon.png" width="96" alt="Fiş Yazıcı simgesi">
</p>

<h1 align="center">Fiş Yazıcı</h1>

<p align="center">
  Mini Bluetooth termal yazıcılar için Windows masaüstü uygulaması: fişi tasarlayın, önizleyin, yazdırın.<br>
  <sub>Python · CustomTkinter · Bleak (BLE) · Pillow</sub>
</p>

---

## Özellikler

- **Blok tabanlı fiş tasarımı.** Fiş metin, fotoğraf, çizgi ve boşluk bloklarından oluşur. Bloklar sıralanabilir, çoğaltılabilir ve silinebilir.
- **Canlı önizleme.** Fişin yazıcıdan nasıl çıkacağı birebir (384 px, siyah-beyaz) gösterilir.
- **Metin.** 6 yazı tipi, 10–120 px boyut, sola/ortaya/sağa hizalama, kalın ve ters renk (siyah zemin). `{tarih}` ve `{saat}` yer tutucuları baskı anında doldurulur.
- **Fotoğraf.**
  - Genişlik, parlaklık, kontrast ve hizalama ayarları.
  - Fotoğraf modu: gri tonlar Floyd–Steinberg titreşimiyle noktalara çevrilir.
  - **Dikey / Yatay yön.** Yatay modda fotoğraf 90° döndürülür ve fişe boylu boyunca basılır. Panoramalar ve geniş ekran görüntüleri için idealdir.
- **Baskı ayarları.** 4 koyuluk seviyesi (Açık, Normal, Koyu, Çok koyu), çoklu kopya, kağıt ilerletme, `Ctrl+P` kısayolu.
- **Bağlantı takibi.** Bağlantı durumu sürekli izlenir (bağlı, yanıt yok, koptu). İsteğe bağlı otomatik bağlanma vardır.
- **Şablonlar.** Fişler JSON olarak kaydedilip açılabilir. Son fiş otomatik saklanır. Örnek: [`ornek_market_fisi.json`](ornek_market_fisi.json).
- **Tema.** Açık, koyu veya sistem teması.

## Desteklenen yazıcılar

Uygulama, ucuz mini termal yazıcıların çoğunun kullandığı `51 78 …` BLE paket protokolünü konuşur (halk arasında "cat printer" protokolü). Yazıcının **384 piksel (58 mm kağıtta ~48 mm) baskı genişliğinde** olması gerekir.

| Model | Durum |
|---|---|
| **X5h** | ✅ Test edildi, tam destekli |
| **X5** ve adı `X5` ile başlayan diğer modeller | ✅ Otomatik bulunur, aynı protokol |
| GB01, GB02, GB03, GT01, MX05, MX06, MX08, MX10, YT01 | ⚠️ Aynı protokol ailesi, **test edilmedi** (aşağıya bakın) |

**Test edilmemiş modeller için:** Uygulama Bluetooth taramasında yalnızca adı `X5` ile başlayan cihazları arar. Başka bir modeli denemek için [`printer.py`](printer.py) dosyasındaki `NAME_PREFIX` değerini yazıcınızın Bluetooth adına göre değiştirin (ör. `"GB0"` veya `"MX"`). Ya da `DEFAULT_ADDRESS` değerine yazıcınızın MAC adresini yazın. Aynı protokol ailesindeki bazı modeller farklı baskı genişliği veya komut farklılıkları kullanabilir. Sonuç iyi değilse koyuluk seviyesini değiştirmeyi deneyin.

Uyumlu olmayanlar: ESC/POS kullanan klasik USB/seri fiş yazıcıları (Epson TM serisi vb.), Phomemo M02 / Peripage gibi farklı protokol kullanan yazıcılar.

## Sistem gereksinimleri

| | |
|---|---|
| **İşletim sistemi** | Windows 10 veya 11 (yazı tipleri Windows'un `Fonts` klasöründen okunur) |
| **Bluetooth** | Bluetooth Low Energy (BLE, Bluetooth 4.0+) destekleyen dahili kart veya USB adaptör |
| **Python** | 3.10 veya üzeri (3.12 ile geliştirildi) |

## Kurulum

```powershell
git clone https://github.com/ByFalcony/thermal-printer-application.git
cd thermal-printer-application
python -m pip install -r requirements.txt
```

### Çalıştırma

`Baslat.bat` dosyasına çift tıklayın. Eksik paketler varsa önce kurulur, sonra uygulama konsol penceresi olmadan açılır.

Ya da doğrudan:

```powershell
python app.py
```

### Masaüstü kısayolu (isteğe bağlı)

Masaüstüne ve Başlat menüsüne simgeli bir kısayol oluşturmak için:

```powershell
python -m pip install pywin32
python kisayol_olustur.py
```

## Kullanım

1. Yazıcıyı açın. **Telefondaki yazıcı uygulamasına bağlı olmadığından emin olun**, çünkü BLE yazıcılar aynı anda tek cihaza bağlanır.
2. **Bağlan** düğmesine basın. "Otomatik bağlan" açıksa uygulama açılışta kendisi bağlanır.
3. Soldaki **Ekle** bölümünden metin, fotoğraf, çizgi veya boşluk ekleyin ve ortadaki panelden düzenleyin.
4. Sağdaki önizlemeyi kontrol edin, koyuluğu ve kopya sayısını seçip **Yazdır** düğmesine basın.

**İpuçları**

- Logo veya yazı içeren resimlerde *Fotoğraf modu*nu kapatmak daha net sonuç verir.
- Fotoğraflar soluk çıkıyorsa kontrastı artırın veya koyuluğu *Koyu* yapın.
- 8 px yaklaşık 1 mm kağıda karşılık gelir.

## Proje yapısı

```
app.py                 Arayüz (CustomTkinter)
printer.py             BLE yazıcı sürücüsü (arka plan asyncio iş parçacığı)
render.py              Blokları 384 px siyah-beyaz görüntüye ve yazıcı satırlarına çevirir
make_icon.py           icon.png / icon.ico üretir
kisayol_olustur.py     Windows kısayolu oluşturur
ornek_market_fisi.json Örnek şablon
Baslat.bat             Tek tıkla başlatıcı
```

Çalışırken oluşan `son_fis.json` (son fiş) ve `ayarlar.json` (kullanıcı ayarları) dosyaları kişiseldir ve depoya eklenmez.

## Sorun giderme

| Sorun | Çözüm |
|---|---|
| "Bluetooth taraması başarısız" | Windows'ta Bluetooth'un açık olduğunu kontrol edin. |
| "Yazıcı bulunamadı" | Yazıcı açık mı ve telefona bağlı değil mi kontrol edin. Model adı `X5` ile başlamıyorsa yukarıdaki `NAME_PREFIX` açıklamasına bakın. |
| "Yanıt yok" durumu | Yazıcı uzaklaşmış veya uyku moduna geçmiş olabilir. Bağlantıyı kesip yeniden bağlanın. |
| Baskı soluk | Koyuluğu artırın, fotoğraflarda kontrastı yükseltin. |
