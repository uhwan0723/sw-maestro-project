package com.soma2026.tikitalka.ui.theme

import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.ui.graphics.Color

// ─────────────────────────────────────────────────────────
// Raw palette — 이 파일 밖에서 직접 참조하지 마세요.
// 화면에서는 MaterialTheme.colorScheme.* 으로 접근하세요.
// ─────────────────────────────────────────────────────────
private object Palette {

    object Light {
        val Bg           = Color(0xFFFAFAFA)
        val Surface      = Color(0xFFFFFFFF)
        val SurfaceAlt   = Color(0xFFF4F5F7)
        val SurfaceMuted = Color(0xFFEEF0F3)

        val Border       = Color(0x140F172A)
        val BorderStrong = Color(0x240F172A)

        val Text          = Color(0xFF0B0F19)
        val TextSecondary = Color(0xFF5B6473)
        val TextTertiary  = Color(0xFF8A93A0)

        val Accent     = Color(0xFF2F6BFF)
        val AccentText = Color(0xFF1E4FCC)

        val Success = Color(0xFF16A34A)
        val Warn    = Color(0xFFE0A100)
        val Danger  = Color(0xFFDC2626)
    }

    object Dark {
        val Bg           = Color(0xFF0A0C10)
        val Surface      = Color(0xFF13161C)
        val SurfaceAlt   = Color(0xFF1A1E26)
        val SurfaceMuted = Color(0xFF222732)

        val Border       = Color(0x14FFFFFF)
        val BorderStrong = Color(0x24FFFFFF)

        val Text          = Color(0xFFF5F7FA)
        val TextSecondary = Color(0xFFA0A8B5)
        val TextTertiary  = Color(0xFF6B7384)

        val Accent     = Color(0xFF4D82FF)
        val AccentText = Color(0xFF7DA3FF)

        val Success = Color(0xFF22C55E)
        val Warn    = Color(0xFFEAB308)
        val Danger  = Color(0xFFF87171)
    }
}

// ─────────────────────────────────────────────────────────
// Material3 ColorScheme 매핑
// ─────────────────────────────────────────────────────────
internal val TikiTalkaLightColorScheme = lightColorScheme(
    primary             = Palette.Light.Accent,
    onPrimary           = Color.White,
    primaryContainer    = Palette.Light.SurfaceAlt,
    onPrimaryContainer  = Palette.Light.AccentText,

    secondary           = Palette.Light.AccentText,
    onSecondary         = Color.White,

    background          = Palette.Light.Bg,
    onBackground        = Palette.Light.Text,

    surface             = Palette.Light.Surface,
    onSurface           = Palette.Light.Text,
    surfaceVariant      = Palette.Light.SurfaceAlt,
    onSurfaceVariant    = Palette.Light.TextSecondary,
    surfaceContainerLow = Palette.Light.SurfaceMuted,

    outline             = Palette.Light.BorderStrong,
    outlineVariant      = Palette.Light.Border,

    error               = Palette.Light.Danger,
    onError             = Color.White,

    tertiary            = Palette.Light.Success,
)

internal val TikiTalkaDarkColorScheme = darkColorScheme(
    primary             = Palette.Dark.Accent,
    onPrimary           = Color.White,
    primaryContainer    = Palette.Dark.SurfaceAlt,
    onPrimaryContainer  = Palette.Dark.AccentText,

    secondary           = Palette.Dark.AccentText,
    onSecondary         = Color.White,

    background          = Palette.Dark.Bg,
    onBackground        = Palette.Dark.Text,

    surface             = Palette.Dark.Surface,
    onSurface           = Palette.Dark.Text,
    surfaceVariant      = Palette.Dark.SurfaceAlt,
    onSurfaceVariant    = Palette.Dark.TextSecondary,
    surfaceContainerLow = Palette.Dark.SurfaceMuted,

    outline             = Palette.Dark.BorderStrong,
    outlineVariant      = Palette.Dark.Border,

    error               = Palette.Dark.Danger,
    onError             = Color.White,

    tertiary            = Palette.Dark.Success,
)
