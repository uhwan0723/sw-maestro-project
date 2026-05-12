package com.soma2026.tikitalka.ui.chat

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Snackbar
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.soma2026.tikitalka.domain.model.ChatMessage
import com.soma2026.tikitalka.domain.model.MessageRole
import com.soma2026.tikitalka.presentation.chat.ChatEffect
import com.soma2026.tikitalka.presentation.chat.ChatIntent
import com.soma2026.tikitalka.presentation.chat.ChatState
import com.soma2026.tikitalka.presentation.chat.ChatViewModel
import com.soma2026.tikitalka.ui.theme.TikiTalkaTheme
import kotlinx.datetime.LocalDateTime
import kotlinx.datetime.number
import org.jetbrains.compose.resources.painterResource
import org.koin.compose.viewmodel.koinViewModel
import tikitalka.composeapp.generated.resources.Res
import tikitalka.composeapp.generated.resources.ico_chatbot_send

@Composable
fun ChatScreen(viewModel: ChatViewModel = koinViewModel()) {
    val state by viewModel.state.collectAsState()
    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(Unit) {
        viewModel.effect.collect { effect ->
            when (effect) {
                is ChatEffect.NavigateBack -> Unit
                is ChatEffect.ShowError -> snackbarHostState.showSnackbar(effect.message)
            }
        }
    }

    ChatContent(
        state = state,
        snackbarHostState = snackbarHostState,
        onInputChange = { viewModel.handleIntent(ChatIntent.UpdateInput(it)) },
        onSend = { viewModel.handleIntent(ChatIntent.SendMessage) },
        onSuggestedQuestionClick = { viewModel.handleIntent(ChatIntent.SelectSuggestedQuestion(it)) },
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun ChatContent(
    state: ChatState,
    snackbarHostState: SnackbarHostState = remember { SnackbarHostState() },
    onInputChange: (String) -> Unit = {},
    onSend: () -> Unit = {},
    onSuggestedQuestionClick: (String) -> Unit = {},
) {
    val listState = rememberLazyListState()

    LaunchedEffect(state.messages.size, state.isSending) {
        val targetIndex = if (state.isSending) state.messages.size else state.messages.size - 1
        if (targetIndex >= 0) listState.animateScrollToItem(targetIndex)
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = "티키 ChatBot",
                        style = MaterialTheme.typography.titleLarge,
                        color = MaterialTheme.colorScheme.onSurface,
                    )
                },
                colors =
                    TopAppBarDefaults.topAppBarColors(
                        containerColor = MaterialTheme.colorScheme.surface,
                    ),
            )
        },
        snackbarHost = {
            SnackbarHost(snackbarHostState) { data -> Snackbar(snackbarData = data) }
        },
        containerColor = MaterialTheme.colorScheme.background,
    ) { innerPadding ->
        Column(
            modifier =
                Modifier
                    .fillMaxSize()
                    .padding(innerPadding)
                    .imePadding(),
        ) {
            Box(modifier = Modifier.weight(1f).fillMaxWidth()) {
                when {
                    state.isLoadingHistory -> {
                        CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
                    }

                    state.messages.isEmpty() && !state.isSending -> {
                        EmptyChatPlaceholder(modifier = Modifier.align(Alignment.Center))
                    }

                    else -> {
                        LazyColumn(
                            state = listState,
                            modifier = Modifier.fillMaxSize(),
                            contentPadding = PaddingValues(horizontal = 16.dp, vertical = 12.dp),
                            verticalArrangement = Arrangement.spacedBy(8.dp),
                        ) {
                            itemsIndexed(state.messages) { index, message ->
                                val localDt = parseToLocalDateTime(message.createdAt)
                                val prevLocalDt = if (index > 0) parseToLocalDateTime(state.messages[index - 1].createdAt) else null
                                val showDateSeparator = index == 0 || datePart(prevLocalDt) != datePart(localDt)
                                if (showDateSeparator && localDt != null) {
                                    DateSeparator(date = formatDate(localDt))
                                    Spacer(modifier = Modifier.height(4.dp))
                                }
                                MessageBubble(
                                    message = message,
                                    time = formatTime(localDt),
                                    onSuggestedQuestionClick = onSuggestedQuestionClick,
                                )
                            }
                            if (state.isSending) {
                                item { ThinkingBubble() }
                            }
                        }
                    }
                }
            }

            ChatInputBar(
                text = state.inputText,
                isSending = state.isSending,
                onTextChange = onInputChange,
                onSend = onSend,
            )
        }
    }
}

@Composable
private fun MessageBubble(
    message: ChatMessage,
    time: String = "",
    onSuggestedQuestionClick: (String) -> Unit = {},
) {
    val isUser = message.role == MessageRole.USER
    val suggestedQuestion = message.suggestedQuestion

    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start,
        verticalAlignment = Alignment.Bottom,
    ) {
        if (isUser && time.isNotEmpty()) {
            Text(
                text = time,
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.6f),
            )
            Spacer(modifier = Modifier.width(4.dp))
        }
        Column(
            modifier =
                Modifier
                    .widthIn(max = 280.dp)
                    .clip(
                        RoundedCornerShape(
                            topStart = 16.dp,
                            topEnd = 16.dp,
                            bottomStart = if (isUser) 16.dp else 4.dp,
                            bottomEnd = if (isUser) 4.dp else 16.dp,
                        ),
                    ).background(
                        if (isUser) {
                            MaterialTheme.colorScheme.primary
                        } else {
                            MaterialTheme.colorScheme.surfaceVariant
                        },
                    ).padding(horizontal = 14.dp, vertical = 10.dp),
        ) {
            Text(
                text = message.content,
                style = MaterialTheme.typography.bodyMedium,
                color =
                    if (isUser) {
                        MaterialTheme.colorScheme.onPrimary
                    } else {
                        MaterialTheme.colorScheme.onSurfaceVariant
                    },
            )
            if (!isUser && suggestedQuestion != null) {
                Spacer(modifier = Modifier.height(8.dp))
                HorizontalDivider(
                    color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.2f),
                )
                Spacer(modifier = Modifier.height(8.dp))
                SuggestedQuestionChip(
                    question = suggestedQuestion,
                    onClick = { onSuggestedQuestionClick(suggestedQuestion) },
                )
            }
        }
        if (!isUser && time.isNotEmpty()) {
            Spacer(modifier = Modifier.width(4.dp))
            Text(
                text = time,
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.6f),
            )
        }
    }
}

@Composable
private fun DateSeparator(date: String) {
    Box(
        modifier = Modifier.fillMaxWidth(),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = date,
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.7f),
            modifier =
                Modifier
                    .background(
                        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f),
                        shape = RoundedCornerShape(12.dp),
                    ).padding(horizontal = 12.dp, vertical = 4.dp),
        )
    }
}

private fun parseToLocalDateTime(createdAt: String): LocalDateTime? {
    if (createdAt.isEmpty()) return null
    // timezone 변환 없이 서버 값 그대로 파싱
    val normalized =
        createdAt
            .replace(" ", "T")
            .substringBefore("Z")
            .substringBefore("+")
            .let { s ->
                val dotIdx = s.indexOf('.')
                if (dotIdx != -1) s.substring(0, minOf(s.length, dotIdx + 4)) else s
            }
    return try {
        LocalDateTime.parse(normalized)
    } catch (_: Exception) {
        null
    }
}

private fun formatTime(local: LocalDateTime?): String {
    local ?: return ""
    return "${local.hour.toString().padStart(2, '0')}:${local.minute.toString().padStart(2, '0')}"
}

private fun formatDate(local: LocalDateTime?): String {
    local ?: return ""
    return "${local.year}년 ${local.month.number}월 ${local.dayOfMonth}일"
}

private fun datePart(local: LocalDateTime?): String {
    local ?: return ""
    return "${local.year}-${local.month.number}-${local.dayOfMonth}"
}

@Composable
private fun SuggestedQuestionChip(
    question: String,
    onClick: () -> Unit,
) {
    Box(
        modifier =
            Modifier
                .clip(RoundedCornerShape(8.dp))
                .background(MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.15f))
                .clickable(onClick = onClick)
                .padding(horizontal = 12.dp, vertical = 6.dp),
    ) {
        Text(
            text = question,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
private fun ThinkingBubble() {
    Box(
        modifier =
            Modifier
                .clip(
                    RoundedCornerShape(
                        topStart = 16.dp,
                        topEnd = 16.dp,
                        bottomStart = 4.dp,
                        bottomEnd = 16.dp,
                    ),
                ).background(MaterialTheme.colorScheme.surfaceVariant)
                .padding(horizontal = 16.dp, vertical = 12.dp),
        contentAlignment = Alignment.Center,
    ) {
        CircularProgressIndicator(
            modifier = Modifier.size(18.dp),
            strokeWidth = 2.dp,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
private fun EmptyChatPlaceholder(modifier: Modifier = Modifier) {
    Column(
        modifier = modifier.padding(horizontal = 32.dp).fillMaxWidth(),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(text = "⚽", style = MaterialTheme.typography.displaySmall)
        Spacer(modifier = Modifier.height(16.dp))
        Text(
            text = "새로운 채팅을 시도하세요",
            style = MaterialTheme.typography.titleMedium,
            color = MaterialTheme.colorScheme.onSurface,
        )
        Spacer(modifier = Modifier.height(8.dp))
        Text(
            text = "축구 이슈에 대해 AI와\n자유롭게 이야기해 보세요!",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
private fun ChatInputBar(
    text: String,
    isSending: Boolean,
    onTextChange: (String) -> Unit,
    onSend: () -> Unit,
) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        color = MaterialTheme.colorScheme.surface,
        shadowElevation = 0.dp,
    ) {
        Column {
            HorizontalDivider(
                thickness = 1.dp,
                color = MaterialTheme.colorScheme.outline.copy(alpha = 0.2f),
            )
            TextField(
                value = text,
                onValueChange = onTextChange,
                modifier =
                    Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp, vertical = 6.dp),
                placeholder = {
                    Text(
                        text = "축구 이슈에 대해 물어보세요",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                },
                trailingIcon = {
                    IconButton(
                        onClick = onSend,
                        enabled = text.isNotBlank() && !isSending,
                    ) {
                        Icon(
                            modifier = Modifier.size(24.dp),
                            painter = painterResource(Res.drawable.ico_chatbot_send),
                            contentDescription = "전송",
                            tint =
                                if (text.isNotBlank() && !isSending) {
                                    MaterialTheme.colorScheme.primary
                                } else {
                                    MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.4f)
                                },
                        )
                    }
                },
                shape = RoundedCornerShape(24.dp),
                colors =
                    TextFieldDefaults.colors(
                        focusedContainerColor = MaterialTheme.colorScheme.surfaceVariant,
                        unfocusedContainerColor = MaterialTheme.colorScheme.surfaceVariant,
                        focusedIndicatorColor = Color.Transparent,
                        unfocusedIndicatorColor = Color.Transparent,
                        disabledIndicatorColor = Color.Transparent,
                    ),
                maxLines = 4,
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                keyboardActions = KeyboardActions(onSend = { onSend() }),
                textStyle = MaterialTheme.typography.bodyMedium,
                enabled = !isSending,
            )
            HorizontalDivider(
                thickness = 1.dp,
                color = MaterialTheme.colorScheme.outline.copy(alpha = 0.2f),
            )
        }
    }
}

// region Preview

private val previewMessages =
    listOf(
        ChatMessage(role = MessageRole.USER, content = "음바페가 진짜 파리로 돌아갈 것 같아요?", suggestedQuestion = null, createdAt = ""),
        ChatMessage(
            role = MessageRole.ASSISTANT,
            content = "현재 여러 매체에서 파리 복귀 가능성을 보도하고 있습니다. 레알 마드리드와의 불화설이 지속되는 가운데, 이적에 열린 태도를 보이고 있다는 소식도 있습니다.",
            suggestedQuestion = "레알 마드리드와 어떤 불화가 있었나요?",
            createdAt = "",
        ),
        ChatMessage(role = MessageRole.USER, content = "이적료는 얼마나 될까요?", suggestedQuestion = null, createdAt = ""),
    )

@Preview
@Composable
private fun ChatContentPreview() {
    TikiTalkaTheme {
        ChatContent(state = ChatState(messages = previewMessages))
    }
}

@Preview
@Composable
private fun ChatContentDarkPreview() {
    TikiTalkaTheme(darkTheme = true) {
        ChatContent(state = ChatState(messages = previewMessages))
    }
}

@Preview
@Composable
private fun ChatContentEmptyPreview() {
    TikiTalkaTheme {
        ChatContent(state = ChatState())
    }
}

@Preview
@Composable
private fun ChatContentSendingPreview() {
    TikiTalkaTheme {
        ChatContent(state = ChatState(messages = previewMessages, isSending = true))
    }
}

// endregion
