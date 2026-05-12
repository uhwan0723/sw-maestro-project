package com.soma2026.tikitalka.data.remote.api

import com.soma2026.tikitalka.data.remote.dto.ChatMessageDto
import com.soma2026.tikitalka.data.remote.dto.SendMessageRequestDto
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.get
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.http.ContentType
import io.ktor.http.contentType

class ChatApi(private val client: HttpClient) {

    suspend fun sendMessage(deviceId: String, message: String): ChatMessageDto =
        client.post("api/chat/message") {
            contentType(ContentType.Application.Json)
            setBody(SendMessageRequestDto(deviceId = deviceId, message = message))
        }.body()

    suspend fun getChatHistory(deviceId: String): List<ChatMessageDto> =
        client.get("api/chat/history/$deviceId").body()
}
