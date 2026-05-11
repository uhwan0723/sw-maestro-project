import type { Intent, Source } from '@/lib/schema';

export const INTENT_LABEL: Record<Intent, string> = {
  recommend_deck: '덱 추천',
  deck_playstyle: '운영법',
  item_pivot: '아이템 피벗',
  patch_summary: '패치 요약',
  other: '기타',
};

const SOURCE_KIND_LABEL: Record<NonNullable<Source['source_kind']>, string> = {
  patch_note_official: '공식 패치',
  meta_site: '메타 사이트',
  community_post: '커뮤니티',
  youtube: '영상',
};

export const getSourceKindLabel = (kind: Source['source_kind']) => {
  if (!kind) {
    return '출처';
  }

  return SOURCE_KIND_LABEL[kind];
};
