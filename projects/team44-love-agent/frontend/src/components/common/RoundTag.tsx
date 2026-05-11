import { Badge } from '@/components/ui/badge';

interface RoundTagProps {
  round: number;
}

export function RoundTag({ round }: RoundTagProps) {
  return (
    <Badge variant="outline" className="text-xs font-medium">
      {round}라운드
    </Badge>
  );
}
