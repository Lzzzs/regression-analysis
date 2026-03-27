export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body style={{ margin: 0, fontFamily: 'ui-sans-serif, system-ui', background: '#f5f7fb' }}>
        {children}
      </body>
    </html>
  );
}
