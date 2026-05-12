package com.soma2026.tikitalka.ui.util

import kotlin.time.Clock
import kotlin.time.Instant
import kotlinx.datetime.LocalDateTime
import kotlinx.datetime.TimeZone
import kotlinx.datetime.toInstant

/**
 * ISO 8601 문자열을 상대 시간 문자열로 변환합니다.
 *
 * 타임존 포함  예) "2024-01-15T10:30:00Z"          → Instant.parse()
 * 타임존 없음  예) "2026-05-09T09:51:36.369921"     → LocalDateTime.parse() + UTC 가정
 *
 * 파싱 실패 시 원본 문자열을 그대로 반환합니다.
 */
fun String.toRelativeTimeString(): String {
    return try {
        val parsedEpochSeconds = if (contains('Z') || contains('+')) {
            Instant.parse(this).epochSeconds
        } else {
            LocalDateTime.parse(this).toInstant(TimeZone.UTC).epochSeconds
        }

        val nowEpochSeconds = Clock.System.now().epochSeconds
        val seconds = (nowEpochSeconds - parsedEpochSeconds).coerceAtLeast(0)

        when {
            seconds < 60         -> "방금 전"
            seconds < 3_600      -> "${seconds / 60}분 전"
            seconds < 86_400     -> "${seconds / 3_600}시간 전"
            seconds < 604_800    -> "${seconds / 86_400}일 전"
            seconds < 2_592_000  -> "${seconds / 604_800}주 전"
            seconds < 31_536_000 -> "${seconds / 2_592_000}달 전"
            else                 -> "${seconds / 31_536_000}년 전"
        }
    } catch (_: Exception) {
        this
    }
}