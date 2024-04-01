import React, { useState } from 'react';
import { Container } from 'react-bootstrap';
import LineGraph from '../Components/LineGraph';
import MarketTable from '../Components/MarketTable';
// import '../styles/App.css';

const HomePage = () => {
    return (
        <div id="page-formatting">
            <Container>
                <div className="page">
                    <h1>Welcome to RocketInsight</h1>
                    <div className="subheading">
                        <h3 align="center">Statistics, analytics and more, to help you make informed decisions with your rEth.</h3>
                    </div>
                    <LineGraph market="AAVE" timeframe={365} />
                    <h2 align="center">Protocols with rEth Assets</h2>
                    {/* <MarketTable showpage={showpage} handlepage={handlepage} /> */}
                    <MarketTable />
                </div>
            </Container>
        </div>
    );
};

export default HomePage;