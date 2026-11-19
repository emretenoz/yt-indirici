# YT İndirici

YouTube videolarını **MP3** veya **MP4** olarak indiren, kendi bilgisayarında çalışan küçük bir web uygulaması. İster videonun tamamını, ister sadece bir kısmını (örneğin 1:20–1:35 arası) indirebilirsin.

Mac'te de Windows'ta da çalışır. Arayüz tarayıcıda açılır ama her şey senin bilgisayarında olur. Hiçbir sunucuya veri gönderilmez.

## Başlatma

- **Mac:** `YT İndirici` uygulamasına çift tıkla. İstersen Dock'a sürükleyip oradan da açabilirsin.
  macOS ilk seferde "açılamıyor" uyarısı verebilir. Bunun sebebi uygulamanın App Store'dan gelmemesi. O zaman şunlardan birini yap:
  - **Sistem Ayarları → Gizlilik ve Güvenlik** sayfasının en altına in ve "YT İndirici" satırındaki **Yine de Aç** düğmesine bas.
  - Eski macOS sürümlerinde uygulamaya sağ tıkla → **Aç** → **Aç** demen yeterli.
- **Windows:** `YT İndirici.vbs` dosyasına çift tıkla. İstersen sağ tık → **Kısayol oluştur** ile masaüstüne kısayol koyabilirsin.
  SmartScreen uyarı verirse **Ek bilgi** → **Yine de çalıştır**'a tıkla.

Tarayıcıda `http://127.0.0.1:8765` kendiliğinden açılır. Arkada pencere açık kalmaz.

İlk açılışta gerekenler kendiliğinden kurulur: Python 3.12, yt-dlp, ffmpeg ve deno. Bu sadece o seferlik bir pencerede yapılır ve birkaç dakika sürebilir.

Uygulama açıkken tekrar çift tıklarsan yeni bir kopya açılmaz, sadece tarayıcı sekmesi açılır.

**Kapatmak için:** sayfanın sağ üstündeki **Uygulamayı kapat** düğmesine bas. Sadece tarayıcı sekmesini kapatırsan uygulama arka planda açık kalır. Bu sorun değil, çok az kaynak kullanır.

`Baslat (Mac).command` ve `Baslat (Windows).bat` dosyaları uygulamayı görünür bir pencerede başlatır. Bunları sadece bir sorun olduğunda hata mesajını görmek için kullan.

## Kendi alan adınla açmak (ör. `indir.siten.com`)

Uygulama yine senin bilgisayarında çalışır, sadece adresi güzelleşir. İnternete açılmaz: bu adres yalnızca uygulamanın açık olduğu bilgisayarda çalışır. Başka biri yazarsa kendi bilgisayarına bağlanmaya çalışır ve hiçbir şey açılmaz.

**1. Cloudflare'de DNS kaydı ekle** (Cloudflare paneli → alan adın → **DNS** → **Records** → **Add record**):

| Alan | Değer |
|---|---|
| Type | `A` |
| Name | `indir` (ya da istediğin bir ad) |
| IPv4 address | `127.0.0.1` |
| Proxy status | **Kapalı (gri bulut, "DNS only")** |

**2.** Bu klasördeki `ayarlar.json` dosyasını aç ve alan adını yaz:

```json
{
  "alan_adi": "indir.siten.com"
}
```

**3.** Uygulamayı kapatıp yeniden aç. Artık `http://indir.siten.com` adresinden açılır. Windows'ta da aynı `ayarlar.json` dosyasını kullan.

**`etenoz.com/ytindir` kısayolu.** Bu kısayol `kanka-agent` sunucusunda (`server.mjs`) tanımlı ve gelen ziyaretçiyi `http://ytindir.etenoz.com` adresine yönlendiriyor. Yönlendirmeyi sunucuya kurmak için `site-icin/ytindir-yonlendirme-kur.sh` betiğini kullandık. Bu betiği bir kez daha çalıştırmak bir şeyi bozmaz.

`YT İndirici.app` Mac başlatıcısının kaynak kodu `mac-baslatici.applescript` dosyasında. Yeniden derlemek için şu komutu kullan: `osacompile -o "YT İndirici.app" mac-baslatici.applescript`

Notlar:
- Adresi yazarken `http://` ile yaz. Tarayıcı `https` denerse ve sayfa açılmazsa bunun sebebi budur.
- Windows ilk açılışta güvenlik duvarı izni sorabilir. **İptal**'e basabilirsin, uygulama yine çalışır.
- 80 portu başka bir program tarafından kullanılıyorsa uygulama `http://indir.siten.com:8765` adresinden açılır.
- Uygulama sadece bu bilgisayardan gelen isteklere cevap verir. Aynı Wi-Fi'deki başka cihazlardan gelen istekleri reddeder.

## Kullanım

1. YouTube bağlantısını yapıştır. Video bilgisi kendiliğinden gelir.
2. **MP4** (video) ya da **MP3** (ses) seç, sonra kaliteyi seç.
3. **Tamamı** ya da **Belirli kısım** seç. Belirli kısım için başlangıç ve bitiş zamanını yaz (`1:23`, `83` veya `1:02:03`). İstersen videoyu oynatıp **Şu an** düğmesine basarak da seçebilirsin.
4. **İndir**'e bas. İndirme bitince dosya tarayıcının İndirilenler klasörüne gelir. Bir kopyası da bu klasördeki `indirilenler/` içine kaydedilir.

## Sorun olursa

YouTube sık sık değişiklik yapıyor. İndirme hata verirse uygulamayı kapatıp yeniden başlat. Her başlatmada yt-dlp kendiliğinden güncellenir.

> Kişisel kullanım içindir. Yalnızca indirme hakkın olan içerikleri indir.
