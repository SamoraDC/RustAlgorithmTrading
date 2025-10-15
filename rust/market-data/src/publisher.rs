use common::{Result, TradingError, messaging::Message};

pub struct MarketDataPublisher {
    address: String,
}

impl MarketDataPublisher {
    pub fn new(address: &str) -> Result<Self> {
        Ok(Self {
            address: address.to_string(),
        })
    }

    pub fn publish(&self, message: Message) -> Result<()> {
        // TODO: Implement ZMQ publishing
        Ok(())
    }
}
