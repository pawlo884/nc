import { Link, Route, Routes } from 'react-router-dom'
import ProductListPage from './pages/ProductListPage'
import ProductDetailPage from './pages/ProductDetailPage'

export default function App() {
  return (
    <div className="app">
      <header className="app-header">
        <Link to="/" className="app-logo">
          MPD <span>Produkty</span>
        </Link>
      </header>
      <main className="app-main">
        <Routes>
          <Route path="/" element={<ProductListPage />} />
          <Route path="/products/:productId" element={<ProductDetailPage />} />
        </Routes>
      </main>
    </div>
  )
}
