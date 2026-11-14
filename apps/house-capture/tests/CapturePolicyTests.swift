import Foundation

@main
struct CapturePolicyTests {
  static func main() {
    // A corner with useful photos must not require three walls or 85% coverage.
    let partial = CaptureQuality(percent: 20, walls: 1, photos: 4)
    guard partial.ready else {
      print("FAIL: a partial area with photos should be ready for review")
      exit(1)
    }
    print("Capture policy tests passed")
  }
}
