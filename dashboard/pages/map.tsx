import dynamic from 'next/dynamic';

// Dynamically import clean OttawaMap with SSR disabled
const OttawaMapClean = dynamic(
  () => import('../components/OttawaMapClean'),
  {
    ssr: false,
    loading: () => (
      <div className="w-full h-full flex items-center justify-center bg-gray-900">
        <div className="text-center text-white">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-4"></div>
          <p>Loading Map...</p>
        </div>
      </div>
    ),
  }
);

export default function Map() {
  return (
    <div className="w-full" style={{ height: 'calc(100vh - 64px)' }}>
      <div className="w-full h-full rounded-lg overflow-hidden border border-dark-border">
        <OttawaMapClean />
      </div>
    </div>
  );
}

