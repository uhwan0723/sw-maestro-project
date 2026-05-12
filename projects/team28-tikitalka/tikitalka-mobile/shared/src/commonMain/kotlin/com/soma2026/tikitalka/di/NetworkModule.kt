package com.soma2026.tikitalka.di

import com.soma2026.tikitalka.data.remote.api.ChatApi
import com.soma2026.tikitalka.data.remote.api.IssueApi
import io.ktor.client.HttpClient
import io.ktor.client.plugins.HttpResponseValidator
import io.ktor.client.plugins.HttpTimeout
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.plugins.defaultRequest
import io.ktor.client.plugins.logging.LogLevel
import io.ktor.client.plugins.logging.Logger
import io.ktor.client.plugins.logging.Logging
import io.ktor.client.request.url
import io.ktor.client.statement.bodyAsText
import io.ktor.serialization.kotlinx.json.json
import kotlinx.serialization.json.Json
import org.koin.dsl.module

fun networkModule(baseUrl: String, isDebug: Boolean = false) = module {
    single {
        HttpClient {
            install(HttpTimeout) {
                requestTimeoutMillis = 90_000
                connectTimeoutMillis = 10_000
            }
            HttpResponseValidator {
                validateResponse { response ->
                    if (!response.status.value.toString().startsWith("2")) {
                        val body = response.bodyAsText()
                        error("HTTP ${response.status.value}: $body")
                    }
                }
            }
            install(ContentNegotiation) {
                json(
                    Json {
                        ignoreUnknownKeys = true
                        isLenient = true
                    },
                )
            }
            if (isDebug) {
                install(Logging) {
                    logger = object : Logger {
                        override fun log(message: String) {
                            println("Ktor: $message")
                        }
                    }
                    level = LogLevel.BODY
                }
            }
            defaultRequest {
                url(baseUrl)
            }
        }
    }
    single { IssueApi(get()) }
    single { ChatApi(get()) }
}