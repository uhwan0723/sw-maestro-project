package com.soma2026.tikitalka.data.service

import com.google.mlkit.common.model.DownloadConditions
import com.google.mlkit.nl.translate.TranslateLanguage
import com.google.mlkit.nl.translate.Translation
import com.google.mlkit.nl.translate.TranslatorOptions
import com.soma2026.tikitalka.domain.service.TranslationLanguage
import com.soma2026.tikitalka.domain.service.TranslationService
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlin.coroutines.resume

class AndroidTranslationService : TranslationService {

    override suspend fun translate(text: String, targetLanguage: TranslationLanguage): Result<String> {
        val (sourceLang, targetLang) = when (targetLanguage) {
            TranslationLanguage.KOREAN -> TranslateLanguage.ENGLISH to TranslateLanguage.KOREAN
            TranslationLanguage.ENGLISH -> TranslateLanguage.KOREAN to TranslateLanguage.ENGLISH
        }

        val options = TranslatorOptions.Builder()
            .setSourceLanguage(sourceLang)
            .setTargetLanguage(targetLang)
            .build()

        val translator = Translation.getClient(options)
        val conditions = DownloadConditions.Builder().build()

        return suspendCancellableCoroutine { cont ->
            translator.downloadModelIfNeeded(conditions)
                .addOnSuccessListener {
                    translator.translate(text)
                        .addOnSuccessListener { translated ->
                            translator.close()
                            if (cont.isActive) cont.resume(Result.success(translated))
                        }
                        .addOnFailureListener { e ->
                            translator.close()
                            if (cont.isActive) cont.resume(Result.failure(e))
                        }
                }
                .addOnFailureListener { e ->
                    translator.close()
                    if (cont.isActive) cont.resume(Result.failure(e))
                }

            cont.invokeOnCancellation { translator.close() }
        }
    }

    override suspend fun isAvailable(): Boolean = true
}