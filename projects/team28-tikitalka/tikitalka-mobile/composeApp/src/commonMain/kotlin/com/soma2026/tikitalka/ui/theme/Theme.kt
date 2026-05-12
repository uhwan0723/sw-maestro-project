package com.soma2026.tikitalka.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable

/**
 * TikiTalka 테마 진입점.
 *
 * 사용:
 *   TikiTalkaTheme {
 *       // ...
 *   }
 *
 * 색상: MaterialTheme.colorScheme.*
 * 타이포: MaterialTheme.typography.*
 * 쉐이프: MaterialTheme.shapes.*
 */
@Composable
fun TikiTalkaTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    val typography = rememberTikiTalkaTypography()

    MaterialTheme(
        colorScheme = if (darkTheme) TikiTalkaDarkColorScheme else TikiTalkaLightColorScheme,
        typography  = typography,
        shapes      = TikiTalkaShapes,
        content     = content,
    )
}
