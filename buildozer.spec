[app]
title = WiFi定位APP
package.name = wifi_loc
package.domain = org.wifi.loc

# 你项目里的文件类型，必须包含 .csv
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,csv

# 应用版本号
version = 0.1

# 依赖库（固定版本，避免兼容性问题）
requirements = python3, kivy==2.2.1, plyer==2.1.0, pandas==2.1.0, numpy==1.26.0, openssl

# 屏幕方向和全屏设置
orientation = portrait
fullscreen = 0

# 安卓权限（WiFi定位必需）
android.permissions = ACCESS_WIFI_STATE, CHANGE_WIFI_STATE, ACCESS_FINE_LOCATION, ACCESS_COARSE_LOCATION, NEARBY_WIFI_DEVICES, INTERNET, ACCESS_BACKGROUND_LOCATION

# 安卓API版本，和我们下载的NDK匹配
android.api = 34
android.minapi = 24
android.sdk = 24
android.ndk = 26b

# 把CSV文件打包进APP资源目录
android.add_assets = fingerprints.csv

# 支持的CPU架构（覆盖绝大多数手机）
android.archs = arm64-v8a, armeabi-v7a

# 备份设置
android.allow_backup = True

[buildozer]
# 日志级别设为2，方便排错
log_level = 2
warn_on_root = 1