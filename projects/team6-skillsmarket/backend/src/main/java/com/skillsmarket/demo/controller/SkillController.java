package com.skillsmarket.demo.controller;

import com.skillsmarket.demo.domain.SkillCategory;
import com.skillsmarket.demo.dto.SkillDetailResponse;
import com.skillsmarket.demo.dto.SkillGenerateRequest;
import com.skillsmarket.demo.dto.SkillGenerateResponse;
import com.skillsmarket.demo.dto.SkillGenerationStatusResponse;
import com.skillsmarket.demo.dto.SkillResponses;
import com.skillsmarket.demo.service.SkillGenerationService;
import com.skillsmarket.demo.service.SkillService;
import com.skillsmarket.demo.service.SseEmitterService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

@Tag(name = "Skill", description = "스킬 조회 API")
@RestController
@RequestMapping("/skills")
@RequiredArgsConstructor
public class SkillController {

    private final SkillService skillService;
    private final SkillGenerationService skillGenerationService;
    private final SseEmitterService sseEmitterService;

    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<Void> handleNotFound(IllegalArgumentException e) {
        return ResponseEntity.notFound().build();
    }

    @Operation(summary = "카테고리별 스킬 목록 조회", description = "카테고리를 기준으로 스킬 목록을 조회합니다.")
    @GetMapping
    public ResponseEntity<SkillResponses> getSkillsByCategory(
            @Parameter(description = "스킬 카테고리 (SPRING_BOOT, REACT, DEVOPS, DATA, ETC)")
            @RequestParam SkillCategory category
    ) {
        SkillResponses response = skillService.findByCategory(category);
        return ResponseEntity.ok(response);
    }

    @Operation(summary = "스킬 생성 요청", description = "AI 기반 스킬 생성을 비동기로 요청합니다.")
    @PostMapping("/generate")
    public ResponseEntity<SkillGenerateResponse> generateSkill(
            @Valid @RequestBody SkillGenerateRequest request
    ) {
        SkillGenerateResponse response = skillGenerationService.submitGenerationRequest(request.userPrompt());
        skillGenerationService.runPipeline(response.requestId());
        return ResponseEntity.status(HttpStatus.ACCEPTED).body(response);
    }

    @Operation(summary = "스킬 생성 요청 상태 조회", description = "요청 ID로 스킬 생성 상태를 조회합니다.")
    @GetMapping("/generate/{requestId}")
    public ResponseEntity<SkillGenerationStatusResponse> getGenerationStatus(
            @Parameter(description = "요청 ID")
            @PathVariable Long requestId
    ) {
        SkillGenerationStatusResponse response = skillGenerationService.getStatus(requestId);
        return ResponseEntity.ok(response);
    }

    @Operation(summary = "스킬 생성 SSE 스트림", description = "요청 ID로 실시간 상태 업데이트를 SSE로 수신합니다.")
    @GetMapping(value = "/generate/{requestId}/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter streamGenerationStatus(
            @Parameter(description = "요청 ID")
            @PathVariable Long requestId
    ) {
        // Validate that the request exists
        skillGenerationService.getStatus(requestId);
        return sseEmitterService.createEmitter(requestId);
    }

    @Operation(summary = "스킬 상세 조회", description = "스킬 ID를 기준으로 스킬 상세 정보를 조회합니다.")
    @GetMapping("/{skillId}")
    public ResponseEntity<SkillDetailResponse> getSkillById(
            @Parameter(description = "스킬 ID")
            @PathVariable Long skillId
    ) {
        SkillDetailResponse response = skillService.findById(skillId);
        return ResponseEntity.ok(response);
    }
}

