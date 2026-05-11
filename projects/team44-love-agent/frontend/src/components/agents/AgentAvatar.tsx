import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import type { AgentId } from '@/types';

interface AgentAvatarProps {
  agentId: AgentId;
  name: string;
  colorKey: string;
  size?: 'xs' | 'sm' | 'md' | 'lg';
}

const sizeClass = {
  xs: 'size-4 text-[10px]',
  sm: 'size-7 text-xs',
  md: 'size-9 text-sm',
  lg: 'size-11 text-base',
};

export function AgentAvatar({ agentId, name, colorKey, size = 'md' }: AgentAvatarProps) {
  const avatarUrl = `https://api.dicebear.com/9.x/avataaars/svg?seed=${agentId}&backgroundColor=transparent`;

  return (
    <Avatar className={sizeClass[size]}>
      <AvatarImage src={avatarUrl} alt={name} />
      <AvatarFallback
        className="font-medium text-white"
        style={{ backgroundColor: `var(--${colorKey})` }}
      >
        {name[0]}
      </AvatarFallback>
    </Avatar>
  );
}
