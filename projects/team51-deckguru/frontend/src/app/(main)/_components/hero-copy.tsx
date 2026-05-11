export function HeroCopy() {
  return (
    <div className="flex max-w-2xl flex-col gap-2 text-left leading-relaxed lg:items-end lg:text-right">
      <h2 className="font-galmuri11 text-2xl leading-tight font-bold text-foreground sm:text-3xl">
        메타를 읽고, 덱을 고르세요
      </h2>
      <p className="max-w-xl text-sm leading-7 text-muted-foreground sm:text-base">
        티어와 스타일에 맞는 <br className="block sm:hidden" />덱 운영 가이드를
        제공합니다
      </p>
    </div>
  );
}
