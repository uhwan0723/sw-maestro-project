package com.soma2026.tikitalka.domain.service

interface TranslationService {
    suspend fun translate(text: String, targetLanguage: TranslationLanguage): Result<String>
    suspend fun isAvailable(): Boolean
}

enum class TranslationLanguage(val code: String, val label: String) {
    KOREAN("ko", "한국어"),
    ENGLISH("en", "English"),
}