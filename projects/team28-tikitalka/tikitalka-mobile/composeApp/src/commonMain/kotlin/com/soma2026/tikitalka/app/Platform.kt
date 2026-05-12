package com.soma2026.tikitalka.app

interface Platform {
    val name: String
}

expect fun getPlatform(): Platform