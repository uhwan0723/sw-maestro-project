import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface ResultCategoryCardProps {
  title: string;
  items: string[];
  colorKey?: string;
}

export function ResultCategoryCard({ title, items, colorKey }: ResultCategoryCardProps) {
  return (
    <Card className="p-4">
      <CardHeader className="p-0 pb-3">
        <CardTitle className="flex items-center gap-2 text-sm font-semibold">
          {colorKey && (
            <span
              className="size-2 rounded-full"
              style={{ backgroundColor: `var(--${colorKey})` }}
            />
          )}
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-1.5 p-0">
        {items.map((item, i) => (
          <div key={i} className="flex items-start gap-2 text-sm">
            <Badge variant="outline" className="mt-0.5 shrink-0 text-[10px]">
              {i + 1}
            </Badge>
            <span>{item}</span>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
