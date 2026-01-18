import dynamic from 'next/dynamic';

// Dynamically import MapLibre map with SSR disabled
const OttawaMap = dynamic(
  () => import('../components/OttawaMap'),
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

export default function Map2() {
  return (
    <div className="w-full" style={{ height: 'calc(100vh - 200px)' }}>
      <div className="mb-4">
        <h1 className="text-4xl font-bold text-white mb-2">Map - Ottawa Region</h1>
        <p className="text-gray-400">Interactive 2D map with geospatial overlays</p>
      </div>
      
      <div className="w-full h-full rounded-lg overflow-hidden border border-dark-border">
        <OttawaMap />
      </div>
    </div>
  );
}

