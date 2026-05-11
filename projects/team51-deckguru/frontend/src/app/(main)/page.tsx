import { MainHero } from '@/app/(main)/_components/main-hero';
import { PatchStatusHeader } from '@/app/(main)/_components/patch-status-header';

export default function MainPage() {
  return (
    <main className="pixel-background flex min-h-dvh w-full flex-col items-center overflow-x-hidden text-foreground">
      <PatchStatusHeader />
      <MainHero />
    </main>
  );
}
