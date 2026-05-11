import localFont from 'next/font/local';

export const galmuri11 = localFont({
  src: [
    {
      path: './galmuri/Galmuri11.woff2',
      weight: '400',
      style: 'normal',
    },
    {
      path: './galmuri/Galmuri11-Bold.woff2',
      weight: '700',
      style: 'bold',
    },
  ],
  variable: '--font-galmuri11',
  display: 'swap',
});

export const galmuri9 = localFont({
  src: [
    {
      path: './galmuri/Galmuri9.woff2',
      weight: '400',
      style: 'normal',
    }
  ],
  variable: '--font-galmuri9',
  display: 'swap',
});
