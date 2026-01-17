import type { AppProps } from 'next/app';
import Layout from '../components/Layout';
import '../styles/globals.css';
import 'cesium/Build/Cesium/Widgets/widgets.css';

export default function App({ Component, pageProps }: AppProps) {
  return (
    <Layout>
      <Component {...pageProps} />
    </Layout>
  );
}

