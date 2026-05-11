package com.skillsmarket.demo.service;

import com.skillsmarket.demo.domain.SkillCategory;
import com.skillsmarket.demo.domain.Skills;
import com.skillsmarket.demo.dto.SkillDetailResponse;
import com.skillsmarket.demo.dto.SkillResponse;
import com.skillsmarket.demo.dto.SkillResponses;
import com.skillsmarket.demo.repository.SkillsRepository;
import java.util.List;
import java.util.stream.Collectors;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class SkillService {

    private final SkillsRepository skillsRepository;

    public SkillResponses findByCategory(SkillCategory category) {
        List<Skills> skills = skillsRepository.findByCategory(category);

        return skills.stream()
                .map(SkillResponse::from)
                .collect(Collectors.collectingAndThen(Collectors.toList(), SkillResponses::new));
    }

    public SkillDetailResponse findById(Long skillId) {
        Skills skill = skillsRepository.findById(skillId)
                .orElseThrow(() -> new IllegalArgumentException("해당 스킬을 찾을 수 없습니다. id=" + skillId));

        return SkillDetailResponse.from(skill);
    }
}
