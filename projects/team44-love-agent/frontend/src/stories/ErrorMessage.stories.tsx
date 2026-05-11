import type { Meta, StoryObj } from '@storybook/nextjs-vite';
import { ErrorMessage } from '@/components/status/ErrorMessage';
import { EmptyState } from '@/components/status/EmptyState';

const meta: Meta = {
  title: 'Status/ErrorAndEmpty',
  tags: ['autodocs'],
};
export default meta;

export const Error: StoryObj = {
  render: () => <ErrorMessage onRetry={() => {}} />,
};

export const ErrorCustomMessage: StoryObj = {
  render: () => <ErrorMessage message="네트워크 연결을 확인해주세요." onRetry={() => {}} />,
};

export const Empty: StoryObj = {
  render: () => <EmptyState />,
};
