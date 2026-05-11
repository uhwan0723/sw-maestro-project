package com.skillsmarket.demo.service;

import com.skillsmarket.demo.domain.Skills;
import com.skillsmarket.demo.dto.SimilarSkillResponse;
import com.skillsmarket.demo.dto.SimilarSkillResponses;
import com.skillsmarket.demo.repository.SkillsRepository;
import java.util.stream.Collectors;
import lombok.RequiredArgsConstructor;
import org.springframework.ai.document.Document;
import org.springframework.ai.vectorstore.SearchRequest;
import org.springframework.ai.vectorstore.VectorStore;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;

@Service
@RequiredArgsConstructor
public class SkillEmbeddingService {

    private final VectorStore vectorStore;
    private final SkillsRepository skillsRepository;

    public void embedAllSkills() {
        List<Skills> skills = skillsRepository.findAll();
        List<String> existingIds = skills.stream()
                .map(s -> "skill-" + s.getId())
                .toList();
        if (!existingIds.isEmpty()) {
            vectorStore.delete(existingIds);
        }

        List<Document> documents = skills.stream()
                .map(skill -> new Document(
                        "skill-" + skill.getId(),
                        skill.getContent(),
                        Map.of(
                                "skillId", skill.getId(),
                                "title", skill.getTitle(),
                                "description", skill.getDescription(),
                                "category", skill.getCategory().name()
                        )
                ))
                .toList();
        if (!documents.isEmpty()) {
            vectorStore.add(documents);
        }
    }

    public SimilarSkillResponses findSimilarSkills(String query, int topK) {
        List<Document> results = vectorStore.similaritySearch(
                SearchRequest.builder()
                        .query(query)
                        .topK(topK)
                        .build()
        );

        return results.stream()
                .map(SimilarSkillResponse::new)
                .collect(Collectors.collectingAndThen(Collectors.toList(), SimilarSkillResponses::new));
    }
}
