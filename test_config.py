# Test AssetMatcherConfig directly
import sys
sys.path.append('ams-back')

try:
    from app.services.enhanced_asset_matcher import AssetMatcherConfig, EnhancedAssetMatcher
    
    print("Testing AssetMatcherConfig...")
    
    # Test with correct parameters
    config = AssetMatcherConfig(
        cache_ttl=3600,
        max_workers=4,
        enable_cache=True,
        data_dir="data/assets"
    )
    
    print(f"Config created successfully: {config}")
    
    # Test creating EnhancedAssetMatcher
    matcher = EnhancedAssetMatcher(config)
    print(f"EnhancedAssetMatcher created successfully: {matcher}")
    
    print("✅ AssetMatcherConfig is working correctly!")
    
except Exception as e:
    print(f"❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()